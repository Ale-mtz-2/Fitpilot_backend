from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Tuple, Dict
from decimal import Decimal
import math

from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MembershipPlan, MembershipSubscription, People, Payment
from app.models.classModel import ClassTemplate, StandingBooking
from app.core.conversions import coerce_int

# Optional imports for standing bookings integration
try:
    from app.crud.classSessionCrud import generate_sessions_from_template
    from app.crud.standingBookingsCrud import create_standing_booking
    STANDING_BOOKINGS_AVAILABLE = True
except ImportError:
    STANDING_BOOKINGS_AVAILABLE = False
    # Create dummy functions so the code doesn't break
    async def create_standing_booking(*args, **kwargs):
        return None

    async def generate_sessions_from_template(*args, **kwargs):
        return []

    class SessionGeneratorService:
        def __init__(self, *args, **kwargs):
            pass
        async def generate_future_sessions(self, *args, **kwargs):
            return {}


@dataclass
class MembershipPlanData:
    id: int
    name: str
    description: Optional[str]
    price: float
    duration_value: int
    duration_unit: str
    class_limit: Optional[int]
    fixed_time_slot: bool
    max_sessions_per_day: Optional[int]
    max_sessions_per_week: Optional[int]
    created_at: datetime


@dataclass
class SubscriptionData:
    id: int
    person_id: int
    plan_id: int
    start_at: datetime
    end_at: datetime
    status: str
    plan_name: str
    person_name: str
    remaining_days: Optional[int]


def _plan_to_data(plan: MembershipPlan) -> MembershipPlanData:
    """Map MembershipPlan model to MembershipPlanData DTO."""
    return MembershipPlanData(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price=float(plan.price),
        duration_value=plan.duration_value,
        duration_unit=plan.duration_unit,
        class_limit=plan.class_limit,
        fixed_time_slot=plan.fixed_time_slot,
        max_sessions_per_day=plan.max_sessions_per_day,
        max_sessions_per_week=plan.max_sessions_per_week,
        created_at=plan.created_at
    )


def _subscription_to_data(
    subscription: MembershipSubscription,
    now: datetime,
) -> SubscriptionData:
    """Map MembershipSubscription model to SubscriptionData DTO."""
    plan_name = getattr(subscription.plan, "name", None) if subscription.plan else None
    person_name = getattr(subscription.person, "full_name", None) if subscription.person else None
    return SubscriptionData(
        id=subscription.id,
        person_id=subscription.person_id,
        plan_id=subscription.plan_id,
        start_at=subscription.start_at,
        end_at=subscription.end_at,
        status=subscription.status,
        plan_name=plan_name or "Sin nombre",
        person_name=person_name or "Sin nombre",
        remaining_days=(subscription.end_at - now).days if subscription.end_at and subscription.end_at > now else 0
    )


def _normalize_to_utc(dt: datetime) -> datetime:
    """Ensure datetime includes timezone info, preserving the provided offset."""
    local_tz = datetime.now().astimezone().tzinfo or timezone.utc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz)
    return dt


def _resolve_payment_amount(
    plan: MembershipPlan,
    payment_amount: Optional[Decimal | float],
) -> Decimal:
    """Resolve payment amount to a Decimal, falling back to plan price."""
    if payment_amount is not None:
        return payment_amount if isinstance(payment_amount, Decimal) else Decimal(str(payment_amount))

    return plan.price if isinstance(plan.price, Decimal) else Decimal(str(plan.price))



def _calculate_subscription_end(plan: MembershipPlan, start_at: datetime) -> datetime:
    """Calculate subscription end datetime based on plan duration."""
    if plan.duration_unit == 'day':
        end_at = start_at + timedelta(days=plan.duration_value)
    elif plan.duration_unit == 'week':
        end_at = start_at + timedelta(weeks=plan.duration_value)
    elif plan.duration_unit == 'month':
        from dateutil.relativedelta import relativedelta
        end_at = start_at + relativedelta(months=plan.duration_value)
    else:
        # Fallback to days to avoid unexpected units
        end_at = start_at + timedelta(days=plan.duration_value)

    # Ajustar para que la membresía finalice al final del día (23:59:59)
    local_tz = datetime.now().astimezone().tzinfo or timezone.utc
    tz = end_at.tzinfo or local_tz
    return end_at.astimezone(tz).replace(hour=23, minute=59, second=59, microsecond=0)

def _align_date_to_weekday(start_date: date, template_weekday: Optional[int]) -> date:
    """Return the first date on or after start_date that matches template_weekday."""
    if template_weekday is None:
        return start_date

    normalized = template_weekday
    if normalized <= 0:
        normalized = 7 if normalized == 0 else ((normalized % 7) or 7)
    elif normalized > 7:
        normalized = ((normalized - 1) % 7) + 1

    base_weekday = start_date.isoweekday()
    delta = (normalized - base_weekday) % 7
    return start_date + timedelta(days=delta)


def _get_plan_window_override(plan: MembershipPlan) -> Optional[int]:
    """
    Check for optional override fields on the plan that define standing booking window in days.
    Supports future schema extensions without requiring code changes.
    """
    override_fields = (
        "standing_window_days",
        "standing_booking_window_days",
        "standing_materialization_days",
    )
    for field in override_fields:
        value = getattr(plan, field, None)
        if value is None:
            continue
        try:
            days = int(value)
        except (TypeError, ValueError):
            continue
        if days > 0:
            return days
    return None


def _calculate_window_end_for_plan(
    plan: MembershipPlan,
    window_start: date,
    subscription_end: date
) -> date:
    """
    Determine the final date (inclusive) for standing booking creation/materialization.

    The logic prioritizes explicit overrides, otherwise derives the window from plan duration:
    - duration_unit == 'day'  -> clamp to the provided number of days.
    - duration_unit == 'week' -> clamp to duration_value * 7 days.
    - For other units (month, year, etc.) fall back to the subscription end date that already
      reflects the configured duration via `_calculate_subscription_end`.
    """
    override_days = _get_plan_window_override(plan)
    if override_days:
        return min(subscription_end, window_start + timedelta(days=override_days - 1))

    try:
        duration_value = int(plan.duration_value)
    except (TypeError, ValueError):
        duration_value = None

    if plan.duration_unit == 'day' and duration_value and duration_value > 0:
        return min(subscription_end, window_start + timedelta(days=duration_value - 1))

    if plan.duration_unit == 'week' and duration_value and duration_value > 0:
        return min(subscription_end, window_start + timedelta(days=(duration_value * 7) - 1))

    # For month/year (or any other unit) rely on subscription_end which already honors duration.
    return subscription_end

async def get_membership_plans(db: AsyncSession) -> List[MembershipPlanData]:
    """Get all available membership plans"""
    result = await db.execute(
        select(MembershipPlan)
        .order_by(MembershipPlan.price.asc())
    )
    plans = result.scalars().all()

    return [_plan_to_data(plan) for plan in plans]


async def get_membership_plan_by_id(db: AsyncSession, plan_id: int) -> Optional[MembershipPlanData]:
    """Get membership plan by ID"""
    plan_id = coerce_int(plan_id)
    if plan_id is None:
        return None

    result = await db.execute(
        select(MembershipPlan)
        .where(MembershipPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return None

    return _plan_to_data(plan)


async def create_membership_plan(
    db: AsyncSession,
    name: str,
    price: float,
    duration_value: int,
    duration_unit: str,
    description: Optional[str] = None,
    class_limit: Optional[int] = None,
    fixed_time_slot: bool = False,
    max_sessions_per_day: Optional[int] = None,
    max_sessions_per_week: Optional[int] = None
) -> MembershipPlan:
    """Create a new membership plan"""
    plan = MembershipPlan(
        name=name,
        description=description,
        price=Decimal(str(price)),
        duration_value=duration_value,
        duration_unit=duration_unit,
        class_limit=class_limit,
        fixed_time_slot=fixed_time_slot,
        max_sessions_per_day=max_sessions_per_day,
        max_sessions_per_week=max_sessions_per_week
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def create_membership_subscription(
    db: AsyncSession,
    person_id: int,
    plan_id: int,
    start_at: Optional[datetime] = None,
    created_by: Optional[int] = None,
    status: str = 'active',
    plan: Optional[MembershipPlan] = None,
    commit: bool = True
) -> MembershipSubscription:
    """Create a new membership subscription."""

    normalized_start = _normalize_to_utc(start_at or datetime.now().astimezone())

    if plan is None:
        plan_result = await db.execute(
            select(MembershipPlan).where(MembershipPlan.id == plan_id)
        )
        plan = plan_result.scalar_one()

    end_at = _calculate_subscription_end(plan, normalized_start)

    subscription = MembershipSubscription(
        person_id=person_id,
        plan_id=plan_id,
        start_at=normalized_start,
        end_at=end_at,
        status=status,
        created_by=created_by
    )

    db.add(subscription)
    await db.flush()

    # Attach plan reference for downstream logic without extra query
    if plan is not None:
        subscription.plan = plan

    if commit:
        await db.commit()
        await db.refresh(subscription)

    return subscription


async def create_payment(
    db: AsyncSession,
    *,
    person_id: int,
    amount: Decimal | float,
    method: str,
    subscription_id: Optional[int] = None,
    status: str = 'COMPLETED',
    paid_at: Optional[datetime] = None,
    provider: Optional[str] = None,
    provider_payment_id: Optional[str] = None,
    external_reference: Optional[str] = None,
    comment: Optional[str] = None,
    recorded_by: Optional[int] = None,
    commit: bool = True
) -> Payment:
    """Record a payment for a person and optional subscription."""
    amount_value = amount if isinstance(amount, Decimal) else Decimal(str(amount))

    payment = Payment(
        person_id=person_id,
        subscription_id=subscription_id,
        amount=amount_value,
        method=method,
        status=status,
        provider=provider,
        provider_payment_id=provider_payment_id,
        external_reference=external_reference,
        comment=comment,
        recorded_by=recorded_by
    )

    if paid_at:
        payment.paid_at = _normalize_to_utc(paid_at)

    db.add(payment)
    await db.flush()

    if commit:
        await db.commit()
        await db.refresh(payment)

    return payment


async def get_member_active_subscription(
    db: AsyncSession,
    member_id: int
) -> Optional[MembershipSubscription]:
    """
    Get the active subscription for a member.

    Note: Uses first() instead of scalar_one_or_none() as a defensive measure.
    While there should only be one active subscription per member (enforced at
    the business logic level), this prevents crashes if duplicates exist.
    Returns the most recent subscription (ordered by end_at desc).
    """
    result = await db.execute(
        select(MembershipSubscription)
        .options(selectinload(MembershipSubscription.plan))
        .where(
            and_(
                MembershipSubscription.person_id == member_id,
                MembershipSubscription.status == 'active'
            )
        )
        .order_by(MembershipSubscription.end_at.desc())
    )
    return result.scalars().first()



async def create_member_enrollment(
    db: AsyncSession,
    *,
    full_name: str,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,  # WhatsApp number stored here
    plan_id: int,
    start_at: Optional[datetime] = None,
    payment_method: str = 'cash',
    payment_amount: Optional[Decimal | float] = None,
    payment_status: str = 'COMPLETED',
    payment_comment: Optional[str] = None,
    payment_provider: Optional[str] = None,
    provider_payment_id: Optional[str] = None,
    external_reference: Optional[str] = None,
    recorded_by: Optional[int] = None
) -> Tuple[People, MembershipSubscription, Payment, MembershipPlan]:
    """Create member, subscription and payment in a single transaction."""
    plan_result = await db.execute(
        select(MembershipPlan).where(MembershipPlan.id == plan_id)
    )
    plan = plan_result.scalar_one()

    normalized_start = _normalize_to_utc(start_at or datetime.now().astimezone())

    from app.crud.membersCrud import create_member as create_member_record

    # Don't start a new transaction - use the existing one from GraphQL
    # Step 1: Create member first (required for payment and subscription)
    person = await create_member_record(
        db=db,
        full_name=full_name,
        email=email,
        phone_number=phone_number,  # WhatsApp stored in phone_number
        commit=False
    )

    # Step 2: Process payment BEFORE creating subscription
    amount_value = _resolve_payment_amount(plan, payment_amount)

    # Create payment first with subscription_id as None (will be updated later)
    payment = await create_payment(
        db=db,
        person_id=person.id,
        subscription_id=None,  # Will be updated after subscription creation
        amount=amount_value,
        method=payment_method,
        status=payment_status,
        comment=payment_comment,
        provider=payment_provider,
        provider_payment_id=provider_payment_id,
        external_reference=external_reference,
        recorded_by=recorded_by,
        commit=False
    )

    # Step 3: Create subscription after payment is processed
    subscription = await create_membership_subscription(
        db=db,
        person_id=person.id,
        plan_id=plan_id,
        start_at=normalized_start,
        created_by=recorded_by,
        status='active',
        plan=plan,
        commit=False
    )

    # Step 4: Update payment with subscription_id
    payment.subscription_id = subscription.id

    # Flush to ensure IDs are available, but don't commit yet
    await db.flush()

    # Refresh objects to get the latest state
    await db.refresh(person)
    await db.refresh(subscription)
    await db.refresh(payment)

    subscription.plan = plan

    return person, subscription, payment, plan


async def _get_templates_in_same_group(
    db: AsyncSession,
    template_id: int
) -> List[ClassTemplate]:
    """
    Get all templates that belong to the same TimeslotGroup.
    Group criteria: same class_type_id + venue_id + start_time_local + instructor_id

    Returns:
        List of ClassTemplate objects ordered by weekday
    """
    if not STANDING_BOOKINGS_AVAILABLE:
        return []

    # Get the reference template
    result = await db.execute(
        select(ClassTemplate)
        .options(
            selectinload(ClassTemplate.class_type),
            selectinload(ClassTemplate.venue)
        )
        .where(ClassTemplate.id == template_id)
    )
    ref_template = result.scalar_one_or_none()

    if not ref_template:
        return []

    # Find all templates with matching group criteria
    query = select(ClassTemplate).options(
        selectinload(ClassTemplate.class_type),
        selectinload(ClassTemplate.venue)
    ).where(
        and_(
            ClassTemplate.class_type_id == ref_template.class_type_id,
            ClassTemplate.venue_id == ref_template.venue_id,
            ClassTemplate.start_time_local == ref_template.start_time_local,
            ClassTemplate.is_active == True
        )
    )

    # Handle instructor_id (both None or same value)
    if ref_template.instructor_id is not None:
        query = query.where(ClassTemplate.instructor_id == ref_template.instructor_id)
    else:
        query = query.where(ClassTemplate.instructor_id.is_(None))

    # Order by weekday for consistent processing
    query = query.order_by(ClassTemplate.weekday)

    result = await db.execute(query)
    templates = result.scalars().all()

    return list(templates)


async def _create_standing_bookings_for_group(
    db: AsyncSession,
    subscription: MembershipSubscription,
    template_id: int,
    seat_id: Optional[int] = None
) -> Tuple[List[int], List[int], Dict[int, date]]:
    """Create standing bookings for ALL templates in the same TimeslotGroup."""
    import logging
    logger = logging.getLogger(__name__)

    if not STANDING_BOOKINGS_AVAILABLE:
        logger.warning("Standing bookings not available, skipping group creation")
        return [], [], {}

    templates = await _get_templates_in_same_group(db, template_id)

    if not templates:
        logger.warning(f"No templates found for group with template_id {template_id}")
        return [], [], {}

    logger.info(f"Creating {len(templates)} standing bookings for group (templates: {[t.id for t in templates]})")

    membership_start = subscription.start_at.date()
    membership_end = subscription.end_at.date()

    standing_booking_ids: List[int] = []
    template_ids_used: List[int] = []
    template_start_dates: Dict[int, date] = {}

    for template in templates:
        try:
            aligned_start = _align_date_to_weekday(
                membership_start,
                getattr(template, "weekday", None)
            )

            if aligned_start > membership_end:
                logger.warning(
                    f"Skipping template {template.id}: aligned start {aligned_start} beyond membership end {membership_end}"
                )
                continue

            standing_booking = await create_standing_booking(
                db=db,
                person_id=subscription.person_id,
                subscription_id=subscription.id,
                template_id=template.id,
                seat_id=seat_id,
                start_date=aligned_start,
                end_date=membership_end
            )

            if standing_booking:
                standing_booking_ids.append(standing_booking.id)
                template_ids_used.append(template.id)
                template_start_dates[template.id] = aligned_start
                logger.info(
                    f"Created standing booking {standing_booking.id} for template {template.id} (weekday {template.weekday}) starting {aligned_start}"
                )
            else:
                logger.warning(f"Failed to create standing booking for template {template.id}")
        except Exception as e:
            logger.error(f"Error creating standing booking for template {template.id}: {e}")
            continue

    logger.info(
        f"Successfully created {len(standing_booking_ids)} standing bookings for templates {template_ids_used}"
    )
    return standing_booking_ids, template_ids_used, template_start_dates

async def _generate_sessions_for_templates(
    db: AsyncSession,
    template_ids: List[int],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    weeks_ahead: Optional[int] = None
) -> dict:
    """
    Generate class sessions for multiple templates.

    Args:
        db: Database session
        template_ids: List of template IDs to generate sessions for
        start_date: Start date for session generation (optional)
        end_date: End date for session generation (optional)
        weeks_ahead: Number of weeks ahead to generate sessions (used if end_date not provided)

    Returns:
        Statistics dict with sessions created per template
    """
    import logging
    from datetime import date, timedelta
    logger = logging.getLogger(__name__)

    if not STANDING_BOOKINGS_AVAILABLE:
        logger.warning("Session generation not available")
        return {"templates_processed": 0, "sessions_created": 0}

    # Determine date range
    if start_date is None:
        start_date = date.today()

    if end_date is None:
        if weeks_ahead is None:
            weeks_ahead = 8
        end_date = start_date + timedelta(weeks=weeks_ahead)

    stats = {
        "templates_processed": 0,
        "sessions_created": 0,
        "templates_with_sessions": []
    }

    logger.info(f"Generating sessions for {len(template_ids)} templates from {start_date} to {end_date}")

    for template_id in template_ids:
        try:
            sessions_created = await generate_sessions_from_template(
                db=db,
                template_id=template_id,
                start_date=start_date,
                end_date=end_date
            )

            stats["templates_processed"] += 1
            stats["sessions_created"] += len(sessions_created)

            if sessions_created:
                stats["templates_with_sessions"].append({
                    "template_id": template_id,
                    "sessions_created": len(sessions_created),
                    "date_range": f"{start_date} to {end_date}"
                })
                logger.info(f"Generated {len(sessions_created)} sessions for template {template_id}")
            else:
                logger.info(f"No new sessions needed for template {template_id}")

        except Exception as e:
            logger.error(f"Error generating sessions for template {template_id}: {e}")
            # Continue with other templates even if one fails
            continue

    logger.info(f"Session generation complete: {stats['sessions_created']} total sessions across {stats['templates_processed']} templates")
    return stats


async def _create_reservations_for_subscription(
    db: AsyncSession,
    subscription_id: int,
    start_date: Optional[date] = None,
    weeks_ahead: Optional[int] = None
) -> dict:
    """
    Helper function to create reservations immediately for a specific subscription.

    Args:
        db: Database session
        subscription_id: The subscription ID to materialize bookings for
        start_date: Start date for materialization (defaults to subscription start)
        weeks_ahead: How many weeks ahead to materialize (optional, calculated from subscription)

    Returns:
        Statistics dictionary with materialization results
    """
    if not STANDING_BOOKINGS_AVAILABLE:
        return {
            "created_reservations": 0,
            "materialized_count": 0
        }

    try:
        from app.crud.standingBookingsCrud import materialize_standing_bookings

        # Get the subscription to determine the materialization window
        subscription_stmt = select(MembershipSubscription).where(
            MembershipSubscription.id == subscription_id
        )
        subscription_result = await db.execute(subscription_stmt)
        subscription = subscription_result.scalar_one_or_none()

        if not subscription:
            return {
                "error": "Subscription not found",
                "created_reservations": 0,
                "materialized_count": 0
            }

        # Calculate window_weeks based on subscription duration if not provided
        if weeks_ahead is None:
            # Calculate weeks from subscription start to end (add 1 week buffer)
            duration_days = (subscription.end_at.date() - subscription.start_at.date()).days
            weeks_ahead = max(1, (duration_days // 7) + 1)

        # Create reservations only for this specific subscription.
        # The materialize function will respect standing_booking.end_date.
        stats = await materialize_standing_bookings(
            db=db,
            window_weeks=weeks_ahead,
            start_date=start_date if start_date else subscription.start_at.date(),
            subscription_id=subscription_id
        )
        return stats
    except Exception as e:
        return {
            "error": str(e),
            "created_reservations": 0,
            "materialized_count": 0
        }


def _assert_materialization_success(materialization_stats: dict) -> None:
    errors = materialization_stats.get("errors") or []
    error_message = materialization_stats.get("error")
    created = int(materialization_stats.get("created_reservations") or 0)
    existing = int(materialization_stats.get("skipped_existing") or 0)
    seat_taken = int(materialization_stats.get("skipped_seat_taken") or 0)
    no_capacity = int(materialization_stats.get("skipped_no_capacity") or 0)
    standing_booking_ids = materialization_stats.get("standing_booking_ids") or []

    if not standing_booking_ids:
        raise ValueError("No se pudieron crear los standing bookings para el horario fijo.")

    materialized_total = created + existing
    reasons = []

    if seat_taken:
        reasons.append(f"asientos ocupados: {seat_taken}")
    if no_capacity:
        reasons.append(f"sin cupo: {no_capacity}")
    if error_message:
        reasons.append(f"error: {error_message}")
    if errors:
        reasons.append(f"errores: {len(errors)}")
    if materialized_total == 0:
        reasons.append("no se generaron reservas")

    if reasons:
        raise ValueError(f"No se pudieron materializar las reservas ({'; '.join(reasons)}).")


async def _handle_fixed_timeslot_effects(
    db: AsyncSession,
    subscription: MembershipSubscription,
    plan: MembershipPlan,
    template_id: int,
    seat_id: Optional[int] = None,
    *,
    auto_materialize: bool = True,
) -> tuple[Optional[int], dict]:
    """Common helper for fixed time-slot effects (group bookings + sessions + materialization).

    Para membresía semanal con horario fijo: crear exactamente UNA class_session por día
    (una por template_id del grupo) dentro de la primera semana del periodo de la suscripción
    y materializar UNA reserva por cada session resultante.
    """
    from datetime import timedelta

    materialization_stats: dict = {
        "created_reservations": 0,
        "materialized_count": 0
    }
    generation_stats: dict = {"sessions_created": 0}

    # Create standing bookings for the whole TimeslotGroup
    standing_booking_ids, template_ids_used, template_start_dates = await _create_standing_bookings_for_group(
        db=db,
        subscription=subscription,
        template_id=template_id,
        seat_id=seat_id,
    )
    primary_id = standing_booking_ids[0] if standing_booking_ids else None

    template_start_dates = template_start_dates or {}
    earliest_template_start = min(template_start_dates.values(), default=subscription.start_at.date())
    window_start = min(subscription.start_at.date(), earliest_template_start)

    subscription_end = subscription.end_at.date()
    window_end = _calculate_window_end_for_plan(
        plan=plan,
        window_start=window_start,
        subscription_end=subscription_end,
    )

    coverage_days = max(1, (window_end - window_start).days + 1)
    weeks_ahead = max(1, math.ceil(coverage_days / 7))

    if standing_booking_ids and auto_materialize:
        created_total = 0
        for tid in template_ids_used:
            template_start = template_start_dates.get(tid, window_start)
            gen_stats = await _generate_sessions_for_templates(
                db=db,
                template_ids=[tid],
                start_date=template_start,
                end_date=window_end,
            )
            created_total += int(gen_stats.get("sessions_created", 0))
        generation_stats["sessions_created"] = created_total

        # Create reservations immediately for the same window
        materialization_stats = await _create_reservations_for_subscription(
            db=db,
            subscription_id=subscription.id,
            start_date=window_start,
            weeks_ahead=weeks_ahead,
        )

    template_start_dates_iso = {tid: dt.isoformat() for tid, dt in template_start_dates.items()}

    # Attach aggregation info
    materialization_stats["generation_stats"] = generation_stats
    materialization_stats["standing_booking_ids"] = standing_booking_ids
    materialization_stats["aligned_start_dates"] = template_start_dates_iso
    materialization_stats["window"] = {
        "start": window_start.isoformat(),
        "end": window_end.isoformat(),
        "weeks_ahead": weeks_ahead,
        "coverage_days": coverage_days,
    }
    return primary_id, materialization_stats


async def renew_subscription_with_standing_booking(
    db: AsyncSession,
    member_id: int,
    plan_id: int,
    template_id: Optional[int] = None,
    seat_id: Optional[int] = None,
    start_at: Optional[datetime] = None,
    payment_method: str = 'cash',
    payment_amount: Optional[Decimal | float] = None,
    payment_status: str = 'COMPLETED',
    payment_comment: Optional[str] = None,
    payment_provider: Optional[str] = None,
    provider_payment_id: Optional[str] = None,
    external_reference: Optional[str] = None,
    recorded_by: Optional[int] = None,
    auto_materialize: bool = True
) -> tuple[MembershipSubscription, Payment, MembershipPlan, Optional[int], dict]:
    """
    Renew a subscription and handle standing booking creation for fixed time slot plans

    Returns:
        - MembershipSubscription: The renewed subscription
        - Payment: The payment record
        - MembershipPlan: The plan details
        - Optional[int]: Standing booking ID if created
        - dict: Materialization stats
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Starting subscription renewal with standing booking for member {member_id}, plan {plan_id}")

    try:
        # Get the plan
        plan_result = await db.execute(
            select(MembershipPlan).where(MembershipPlan.id == plan_id)
        )
        plan = plan_result.scalar_one()
        logger.info(f"Found plan: {plan.name} (${plan.price})")
    except Exception as e:
        logger.error(f"Failed to get plan {plan_id}: {e}")
        raise ValueError(f"Plan {plan_id} not found") from e

    # Get current active subscription to calculate renewal start date
    current_subscription = await get_member_active_subscription(db, member_id)

    needs_standing_booking = plan.fixed_time_slot or template_id is not None

    # If template_id/seat_id not provided, try to preserve them from the previous subscription's standing bookings.
    if not template_id and current_subscription:
        if plan.fixed_time_slot:
            logger.info("Plan requires fixed_time_slot but no template_id provided. Looking for previous standing booking...")
        else:
            logger.info("No template_id provided. Checking for previous standing booking to preserve schedule...")

        # Get the most recent standing booking from the current subscription
        previous_sb_result = await db.execute(
            select(StandingBooking)
            .where(StandingBooking.subscription_id == current_subscription.id)
            .order_by(StandingBooking.created_at.desc())
            .limit(1)
        )
        previous_sb = previous_sb_result.scalars().first()

        if previous_sb:
            template_id = previous_sb.template_id
            seat_id = previous_sb.seat_id if not seat_id else seat_id
            needs_standing_booking = True
            logger.info(
                f"Preserving template_id={template_id}, seat_id={seat_id} from previous standing booking {previous_sb.id}"
            )
        else:
            logger.warning(f"No previous standing booking found for subscription {current_subscription.id}")

    if start_at is None:
        if current_subscription and current_subscription.end_at:
            # Start renewal from current subscription end date
            normalized_start = _normalize_to_utc(current_subscription.end_at)
        else:
            # No active subscription, start from now
            normalized_start = _normalize_to_utc(datetime.now().astimezone())
    else:
        normalized_start = _normalize_to_utc(start_at)

    # Expire all existing active subscriptions before creating the new one
    # This prevents having multiple active subscriptions for the same member
    logger.info(f"Expiring existing active subscriptions for member {member_id}")

    # First, get IDs of subscriptions to expire
    expired_subs_result = await db.execute(
        select(MembershipSubscription.id)
        .where(
            and_(
                MembershipSubscription.person_id == member_id,
                MembershipSubscription.status == 'active'
            )
        )
    )
    expired_subscription_ids = [row[0] for row in expired_subs_result.fetchall()]

    # Expire the subscriptions
    await db.execute(
        update(MembershipSubscription)
        .where(
            and_(
                MembershipSubscription.person_id == member_id,
                MembershipSubscription.status == 'active'
            )
        )
        .values(status='expired', updated_at=datetime.now(timezone.utc))
    )

    # Also expire standing bookings associated with the expired subscriptions
    if expired_subscription_ids:
        logger.info(f"Expiring standing bookings for {len(expired_subscription_ids)} expired subscriptions")
        await db.execute(
            update(StandingBooking)
            .where(
                and_(
                    StandingBooking.subscription_id.in_(expired_subscription_ids),
                    StandingBooking.status == 'active'
                )
            )
            .values(status='canceled')  # Note: 'canceled' not 'cancelled'
        )

    await db.flush()  # Ensure the updates are applied before creating the new subscription

    # Create new subscription
    subscription = await create_membership_subscription(
        db=db,
        person_id=member_id,
        plan_id=plan_id,
        start_at=normalized_start,
        created_by=recorded_by,
        commit=False
    )

    # Calculate payment amount
    amount_value = _resolve_payment_amount(plan, payment_amount)

    # Create payment
    payment = await create_payment(
        db=db,
        person_id=member_id,
        subscription_id=subscription.id,
        amount=amount_value,
        method=payment_method,
        status=payment_status,
        comment=payment_comment,
        provider=payment_provider,
        provider_payment_id=provider_payment_id,
        external_reference=external_reference,
        recorded_by=recorded_by,
        commit=False
    )

    standing_booking_id = None
    materialization_stats = {
        "created_reservations": 0,
        "materialized_count": 0
    }

    # Handle standing booking for fixed time slot plans or explicit template selection
    if needs_standing_booking:
        if not template_id:
            raise ValueError("Debe seleccionar un horario para renovar este plan.")
        if not auto_materialize:
            raise ValueError("La renovacion requiere materializar reservas automaticamente.")
        logger.info(f"Handling fixed time-slot effects for template {template_id}")
        standing_booking_id, materialization_stats = await _handle_fixed_timeslot_effects(
            db=db,
            subscription=subscription,
            plan=plan,
            template_id=template_id,
            seat_id=seat_id,
            auto_materialize=auto_materialize,
        )
        _assert_materialization_success(materialization_stats)

    # Commit transaction
    logger.info(f"Committing renewal transaction for subscription {subscription.id}")
    await db.commit()

    # Refresh objects
    await db.refresh(subscription)
    await db.refresh(payment)
    await db.refresh(plan)

    return subscription, payment, plan, standing_booking_id, materialization_stats


async def create_member_enrollment_with_standing_booking(
    db: AsyncSession,
    full_name: str,
    plan_id: int,
    template_id: Optional[int] = None,
    seat_id: Optional[int] = None,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    start_at: Optional[datetime] = None,
    payment_method: str = 'cash',
    payment_amount: Optional[Decimal | float] = None,
    payment_status: str = 'COMPLETED',
    payment_comment: Optional[str] = None,
    payment_provider: Optional[str] = None,
    provider_payment_id: Optional[str] = None,
    external_reference: Optional[str] = None,
    recorded_by: Optional[int] = None,
    auto_materialize: bool = True
) -> tuple[People, MembershipSubscription, Payment, MembershipPlan, Optional[int], dict]:
    """
    Create member enrollment with automatic standing booking for fixed time slot plans

    Returns:
        - People: The created member
        - MembershipSubscription: The subscription
        - Payment: The payment record
        - MembershipPlan: The plan details
        - Optional[int]: Standing booking ID if created
        - dict: Materialization stats
    """
    # Use the existing enrollment function
    person, subscription, payment, plan = await create_member_enrollment(
        db=db,
        full_name=full_name,
        email=email,
        phone_number=phone_number,  # WhatsApp number stored in phone_number
        plan_id=plan_id,
        start_at=start_at,
        payment_method=payment_method,
        payment_amount=payment_amount,
        payment_status=payment_status,
        payment_comment=payment_comment,
        payment_provider=payment_provider,
        provider_payment_id=provider_payment_id,
        external_reference=external_reference,
        recorded_by=recorded_by
    )

    standing_booking_id = None
    materialization_stats = {
        "created_reservations": 0,
        "materialized_count": 0
    }

    # Handle fixed time-slot effects via shared helper
    if template_id:
        standing_booking_id, materialization_stats = await _handle_fixed_timeslot_effects(
            db=db,
            subscription=subscription,
            plan=plan,
            template_id=template_id,
            seat_id=seat_id,
            auto_materialize=auto_materialize,
        )

    # Final commit
    await db.commit()

    return person, subscription, payment, plan, standing_booking_id, materialization_stats


async def get_active_subscriptions(db: AsyncSession, limit: int = 100) -> List[SubscriptionData]:
    """Get list of active subscriptions"""
    now = datetime.now().astimezone()

    result = await db.execute(
        select(MembershipSubscription)
        .options(
            selectinload(MembershipSubscription.person),
            selectinload(MembershipSubscription.plan)
        )
        .where(
            and_(
                MembershipSubscription.status == 'active',
                MembershipSubscription.end_at > now
            )
        )
        .order_by(MembershipSubscription.end_at.asc())
        .limit(limit)
    )
    subscriptions = result.scalars().all()

    return [_subscription_to_data(sub, now) for sub in subscriptions]


async def get_expiring_subscriptions(db: AsyncSession, days_ahead: int = 7) -> List[SubscriptionData]:
    """Get subscriptions that will expire in the next N days"""
    now = datetime.now().astimezone()
    future_date = now + timedelta(days=days_ahead)

    result = await db.execute(
        select(MembershipSubscription)
        .options(
            selectinload(MembershipSubscription.person),
            selectinload(MembershipSubscription.plan)
        )
        .where(
            and_(
                MembershipSubscription.status == 'active',
                MembershipSubscription.end_at.between(now, future_date)
            )
        )
        .order_by(MembershipSubscription.end_at.asc())
    )
    subscriptions = result.scalars().all()

    return [_subscription_to_data(sub, now) for sub in subscriptions]


async def get_membership_subscriptions(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[SubscriptionData]:
    """Get membership subscriptions with optional filters"""
    now = datetime.now().astimezone()

    # Base query
    query = select(MembershipSubscription).options(
        selectinload(MembershipSubscription.person),
        selectinload(MembershipSubscription.plan)
    )

    # Apply filters
    conditions = []

    if status:
        conditions.append(MembershipSubscription.status == status)

    if search:
        # Search in person name, phone, or email
        search_term = f"%{search.lower()}%"
        conditions.append(
            MembershipSubscription.person.has(
                or_(
                    People.full_name.ilike(search_term),
                    People.phone_number.ilike(search_term),
                    People.email.ilike(search_term)
                )
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Order and pagination
    query = query.order_by(MembershipSubscription.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    subscriptions = result.scalars().all()

    return [_subscription_to_data(sub, now) for sub in subscriptions]
