"""
Standing Bookings CRUD operations for FitPilot.
Handles recurring reservations (reservativos) for fixed schedule memberships.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from sqlalchemy import select, and_, or_, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.classModel import (
    StandingBooking, StandingBookingException, ClassTemplate, ClassType,
    ClassSession, Reservation
)
from app.models.userModel import People
from app.models.venueModel import Venue, Seat
from app.models.membershipsModel import MembershipSubscription


@dataclass
class StandingBookingData:
    """Data transfer object for Standing Booking with related data"""
    id: int
    person_id: int
    subscription_id: int
    template_id: int
    seat_id: Optional[int]
    start_date: date
    end_date: date
    status: str
    created_at: datetime

    # Related data
    person_name: Optional[str] = None
    template_name: Optional[str] = None
    class_type_name: Optional[str] = None
    venue_name: Optional[str] = None
    seat_label: Optional[str] = None
    weekday: Optional[int] = None
    start_time_local: Optional[str] = None


@dataclass
class ClassTypeData:
    """Data transfer object for Class Type"""
    id: int
    code: str
    name: str
    description: Optional[str] = None


@dataclass
class ClassTemplateData:
    """Data transfer object for Class Template with related data"""
    id: int
    class_type_id: int
    venue_id: int
    default_capacity: Optional[int]
    default_duration_min: int
    weekday: int
    start_time_local: str
    instructor_id: Optional[int]
    name: Optional[str]
    is_active: bool

    # Related data
    class_type_name: Optional[str] = None
    venue_name: Optional[str] = None
    instructor_name: Optional[str] = None


@dataclass
class SeatData:
    """Data transfer object for Seat with availability"""
    id: int
    label: str
    venue_id: int
    is_active: bool
    seat_type_name: Optional[str] = None
    is_available: bool = True


async def get_class_types(db: AsyncSession) -> List[ClassTypeData]:
    """Get all class types"""
    stmt = select(ClassType).order_by(ClassType.name)
    result = await db.execute(stmt)
    class_types = result.scalars().all()

    return [
        ClassTypeData(
            id=ct.id,
            code=ct.code,
            name=ct.name,
            description=ct.description
        )
        for ct in class_types
    ]


async def get_class_templates(
    db: AsyncSession,
    class_type_id: Optional[int] = None,
    venue_id: Optional[int] = None,
    active_only: bool = True
) -> List[ClassTemplateData]:
    """Get class templates with optional filtering"""
    stmt = select(ClassTemplate).options(
        joinedload(ClassTemplate.class_type),
        joinedload(ClassTemplate.venue)
    )

    if active_only:
        stmt = stmt.where(ClassTemplate.is_active == True)

    if class_type_id:
        stmt = stmt.where(ClassTemplate.class_type_id == class_type_id)

    if venue_id:
        stmt = stmt.where(ClassTemplate.venue_id == venue_id)

    stmt = stmt.order_by(ClassTemplate.weekday, ClassTemplate.start_time_local)

    result = await db.execute(stmt)
    templates = result.scalars().all()

    return [
        ClassTemplateData(
            id=tmpl.id,
            class_type_id=tmpl.class_type_id,
            venue_id=tmpl.venue_id,
            default_capacity=tmpl.default_capacity,
            default_duration_min=tmpl.default_duration_min,
            weekday=tmpl.weekday,
            start_time_local=str(tmpl.start_time_local),
            instructor_id=tmpl.instructor_id,
            name=tmpl.name,
            is_active=tmpl.is_active,
            class_type_name=tmpl.class_type.name if tmpl.class_type else None,
            venue_name=tmpl.venue.name if tmpl.venue else None
        )
        for tmpl in templates
    ]


async def get_available_seats_for_template(
    db: AsyncSession,
    template_id: int,
    date_to_check: Optional[date] = None
) -> List[SeatData]:
    """
    Get available seats for a specific template.

    If date_to_check is provided: Returns seats not reserved for that specific session date
    If date_to_check is None: Returns seats without active standing bookings (for standing booking creation)
    """
    # First get the template to know the venue
    template_stmt = select(ClassTemplate).where(ClassTemplate.id == template_id)
    template_result = await db.execute(template_stmt)
    template = template_result.scalar_one_or_none()

    if not template:
        return []

    # Get all seats for this venue
    seats_stmt = select(Seat).where(
        and_(
            Seat.venue_id == template.venue_id,
            Seat.is_active == True
        )
    ).order_by(Seat.label)

    seats_result = await db.execute(seats_stmt)
    seats = seats_result.scalars().all()

    # If no specific date provided, check for active standing bookings
    # (used when creating a new standing booking to show which seats are permanently taken)
    if not date_to_check:
        # Get seat IDs that have active standing bookings for this template
        standing_bookings_stmt = select(StandingBooking.seat_id).where(
            and_(
                StandingBooking.template_id == template_id,
                StandingBooking.status == 'active',
                StandingBooking.seat_id.isnot(None)
            )
        )
        standing_bookings_result = await db.execute(standing_bookings_stmt)
        occupied_seat_ids = {seat_id for seat_id, in standing_bookings_result.fetchall() if seat_id}

        return [
            SeatData(
                id=seat.id,
                label=seat.label,
                venue_id=seat.venue_id,
                is_active=seat.is_active,
                is_available=seat.id not in occupied_seat_ids
            )
            for seat in seats
        ]

    if isinstance(date_to_check, datetime):
        date_to_check = date_to_check.date()

    # Check which seats are taken for the specific date
    # Find the session for this template on the given date
    session_stmt = select(ClassSession).where(
        and_(
            ClassSession.template_id == template_id,
            func.date(ClassSession.start_at) == date_to_check
        )
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    taken_seat_ids = set()
    if session:
        # Get reserved seat IDs for this session
        reservations_stmt = select(Reservation.seat_id).where(
            and_(
                Reservation.session_id == session.id,
                Reservation.seat_id.isnot(None),
                Reservation.status.in_(['reserved', 'checked_in'])
            )
        )
        reservations_result = await db.execute(reservations_stmt)
        taken_seat_ids = {seat_id for seat_id, in reservations_result.fetchall() if seat_id}

    return [
        SeatData(
            id=seat.id,
            label=seat.label,
            venue_id=seat.venue_id,
            is_active=seat.is_active,
            is_available=seat.id not in taken_seat_ids
        )
        for seat in seats
    ]


async def create_standing_booking(
    db: AsyncSession,
    person_id: int,
    subscription_id: int,
    template_id: int,
    start_date: date,
    end_date: date,
    seat_id: Optional[int] = None
) -> StandingBooking:
    """Create a new standing booking"""

    # Validate that the subscription exists and is active
    subscription_stmt = select(MembershipSubscription).where(
        and_(
            MembershipSubscription.id == subscription_id,
            MembershipSubscription.person_id == person_id,
            MembershipSubscription.status == 'active'
        )
    )
    subscription_result = await db.execute(subscription_stmt)
    subscription = subscription_result.scalar_one_or_none()

    if not subscription:
        raise ValueError("Active subscription not found for this person")

    # Validate that the template exists
    template_stmt = select(ClassTemplate).where(ClassTemplate.id == template_id)
    template_result = await db.execute(template_stmt)
    template = template_result.scalar_one_or_none()

    if not template:
        raise ValueError("Class template not found")

    if not template.is_active:
        raise ValueError("Class template is not active")

    # Validate seat if provided
    if seat_id:
        seat_stmt = select(Seat).where(
            and_(
                Seat.id == seat_id,
                Seat.venue_id == template.venue_id,
                Seat.is_active == True
            )
        )
        seat_result = await db.execute(seat_stmt)
        seat = seat_result.scalar_one_or_none()

        if not seat:
            raise ValueError("Seat not found or not available for this venue")

    # Check for existing active standing booking for same person/template
    existing_stmt = select(StandingBooking).where(
        and_(
            StandingBooking.person_id == person_id,
            StandingBooking.template_id == template_id,
            StandingBooking.status == 'active'
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise ValueError("Active standing booking already exists for this person and template")

    # Check if the seat is already taken by another person for this template
    if seat_id:
        seat_taken_stmt = select(StandingBooking).where(
            and_(
                StandingBooking.template_id == template_id,
                StandingBooking.seat_id == seat_id,
                StandingBooking.status == 'active',
                StandingBooking.person_id != person_id  # Different person
            )
        )
        seat_taken_result = await db.execute(seat_taken_stmt)
        seat_taken = seat_taken_result.scalar_one_or_none()

        if seat_taken:
            raise ValueError(f"Seat {seat_id} is already reserved by another person for this template")

    # Create the standing booking
    standing_booking = StandingBooking(
        person_id=person_id,
        subscription_id=subscription_id,
        template_id=template_id,
        seat_id=seat_id,
        start_date=start_date,
        end_date=end_date,
        status='active'
    )

    db.add(standing_booking)
    await db.flush()  # Get the ID

    return standing_booking


async def get_standing_booking_by_id(
    db: AsyncSession,
    standing_booking_id: int
) -> Optional[StandingBookingData]:
    """Get standing booking by ID with related data"""
    stmt = select(StandingBooking).options(
        joinedload(StandingBooking.person),
        joinedload(StandingBooking.template).joinedload(ClassTemplate.class_type),
        joinedload(StandingBooking.template).joinedload(ClassTemplate.venue)
    ).where(StandingBooking.id == standing_booking_id)

    result = await db.execute(stmt)
    sb = result.scalar_one_or_none()

    if not sb:
        return None

    return StandingBookingData(
        id=sb.id,
        person_id=sb.person_id,
        subscription_id=sb.subscription_id,
        template_id=sb.template_id,
        seat_id=sb.seat_id,
        start_date=sb.start_date,
        end_date=sb.end_date,
        status=sb.status,
        created_at=sb.created_at,
        person_name=sb.person.full_name if sb.person else None,
        template_name=sb.template.name if sb.template else None,
        class_type_name=sb.template.class_type.name if sb.template and sb.template.class_type else None,
        venue_name=sb.template.venue.name if sb.template and sb.template.venue else None,
        weekday=sb.template.weekday if sb.template else None,
        start_time_local=str(sb.template.start_time_local) if sb.template else None
    )


async def get_standing_bookings(
    db: AsyncSession,
    person_id: Optional[int] = None,
    template_id: Optional[int] = None,
    status: Optional[str] = None,
    active_only: bool = False
) -> List[StandingBookingData]:
    """Get standing bookings with optional filtering"""
    stmt = select(StandingBooking).options(
        joinedload(StandingBooking.person),
        joinedload(StandingBooking.template).joinedload(ClassTemplate.class_type),
        joinedload(StandingBooking.template).joinedload(ClassTemplate.venue)
    )

    if person_id:
        stmt = stmt.where(StandingBooking.person_id == person_id)

    if template_id:
        stmt = stmt.where(StandingBooking.template_id == template_id)

    if status:
        stmt = stmt.where(StandingBooking.status == status)
    elif active_only:
        stmt = stmt.where(StandingBooking.status == 'active')

    stmt = stmt.order_by(StandingBooking.created_at.desc())

    result = await db.execute(stmt)
    standing_bookings = result.scalars().all()

    return [
        StandingBookingData(
            id=sb.id,
            person_id=sb.person_id,
            subscription_id=sb.subscription_id,
            template_id=sb.template_id,
            seat_id=sb.seat_id,
            start_date=sb.start_date,
            end_date=sb.end_date,
            status=sb.status,
            created_at=sb.created_at,
            person_name=sb.person.full_name if sb.person else None,
            template_name=sb.template.name if sb.template else None,
            class_type_name=sb.template.class_type.name if sb.template and sb.template.class_type else None,
            venue_name=sb.template.venue.name if sb.template and sb.template.venue else None,
            weekday=sb.template.weekday if sb.template else None,
            start_time_local=str(sb.template.start_time_local) if sb.template else None
        )
        for sb in standing_bookings
    ]


async def update_standing_booking_status(
    db: AsyncSession,
    standing_booking_id: int,
    new_status: str
) -> StandingBooking:
    """Update standing booking status"""
    if new_status not in ['active', 'paused', 'canceled']:
        raise ValueError("Invalid status. Must be 'active', 'paused', or 'canceled'")

    stmt = select(StandingBooking).where(StandingBooking.id == standing_booking_id)
    result = await db.execute(stmt)
    standing_booking = result.scalar_one_or_none()

    if not standing_booking:
        raise ValueError("Standing booking not found")

    standing_booking.status = new_status
    await db.flush()

    return standing_booking


async def create_standing_booking_exception(
    db: AsyncSession,
    standing_booking_id: int,
    session_date: date,
    action: str,
    new_session_id: Optional[int] = None,
    notes: Optional[str] = None
) -> StandingBookingException:
    """Create an exception for a standing booking"""
    if action not in ['skip', 'reschedule']:
        raise ValueError("Action must be 'skip' or 'reschedule'")

    if action == 'reschedule' and not new_session_id:
        raise ValueError("new_session_id is required for reschedule action")

    # Validate standing booking exists
    sb_stmt = select(StandingBooking).where(StandingBooking.id == standing_booking_id)
    sb_result = await db.execute(sb_stmt)
    standing_booking = sb_result.scalar_one_or_none()

    if not standing_booking:
        raise ValueError("Standing booking not found")

    # Validate new session if provided
    if new_session_id:
        session_stmt = select(ClassSession).where(ClassSession.id == new_session_id)
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        if not session:
            raise ValueError("New session not found")

    # Check for existing exception on this date
    existing_stmt = select(StandingBookingException).where(
        and_(
            StandingBookingException.standing_booking_id == standing_booking_id,
            StandingBookingException.session_date == session_date
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise ValueError("Exception already exists for this date")

    # Create the exception
    exception = StandingBookingException(
        standing_booking_id=standing_booking_id,
        session_date=session_date,
        action=action,
        new_session_id=new_session_id,
        notes=notes
    )

    db.add(exception)
    await db.flush()

    return exception


# Materialization Algorithm
async def materialize_standing_bookings(
    db: AsyncSession,
    window_weeks: int = 8,
    start_date: Optional[date] = None,
    subscription_id: Optional[int] = None,
    template_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Materialize standing bookings into actual reservations.

    This is the core algorithm that creates future reservations based on
    standing booking rules, respecting capacity and seat constraints.

    Args:
        db: Database session
        window_weeks: How many weeks ahead to materialize (default 8)
        start_date: Start date for materialization (default today)
        subscription_id: Optional subscription ID to filter standing bookings (default None for all)
        template_id: Optional template ID to filter standing bookings (default None for all)

    Returns:
        Dictionary with materialization results and stats
    """
    if start_date is None:
        start_date = date.today()

    end_date = start_date + timedelta(weeks=window_weeks)

    stats = {
        'processed_bookings': 0,
        'created_reservations': 0,
        'skipped_no_capacity': 0,
        'skipped_seat_taken': 0,
        'skipped_existing': 0,
        'skipped_exceptions': 0,
        'errors': []
    }

    # Get all active standing bookings with optional subscription filter
    conditions = [
        StandingBooking.status == 'active',
        StandingBooking.start_date <= end_date,
        StandingBooking.end_date >= start_date
    ]

    if subscription_id is not None:
        conditions.append(StandingBooking.subscription_id == subscription_id)

    if template_id is not None:
        conditions.append(StandingBooking.template_id == template_id)

    stmt = select(StandingBooking).options(
        joinedload(StandingBooking.template),
        joinedload(StandingBooking.person)
    ).where(and_(*conditions))

    result = await db.execute(stmt)
    standing_bookings = result.scalars().all()

    for sb in standing_bookings:
        stats['processed_bookings'] += 1

        try:
            await _materialize_single_standing_booking(db, sb, start_date, end_date, stats)
        except Exception as e:
            error_msg = f"Error processing standing booking {sb.id}: {str(e)}"
            stats['errors'].append(error_msg)
            continue

    stats["materialized_count"] = stats["created_reservations"]
    stats["reservations_created"] = stats["created_reservations"]
    return stats


async def materialize_standing_bookings_for_session(
    db: AsyncSession,
    session_id: int,
) -> Dict[str, Any]:
    """
    Materialize standing bookings into reservations for a single session.
    Intended for real-time flows when a new session is created.
    """
    stats = {
        "processed_bookings": 0,
        "created_reservations": 0,
        "skipped_no_capacity": 0,
        "skipped_seat_taken": 0,
        "skipped_existing": 0,
        "skipped_exceptions": 0,
        "errors": [],
    }

    session_stmt = select(ClassSession).options(
        joinedload(ClassSession.template)
    ).where(ClassSession.id == session_id)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if not session or not session.template_id or session.status != "scheduled":
        stats["materialized_count"] = 0
        stats["reservations_created"] = 0
        return stats

    template = session.template
    if not template or not template.is_active:
        stats["materialized_count"] = 0
        stats["reservations_created"] = 0
        return stats

    session_date = session.start_at.date()

    standing_stmt = select(StandingBooking).where(
        and_(
            StandingBooking.template_id == session.template_id,
            StandingBooking.status == "active",
            StandingBooking.start_date <= session_date,
            StandingBooking.end_date >= session_date,
        )
    )
    standing_result = await db.execute(standing_stmt)
    standing_bookings = standing_result.scalars().all()

    for sb in standing_bookings:
        stats["processed_bookings"] += 1
        try:
            await _create_reservation_if_possible(
                db, sb, session.id, stats, source="standing"
            )
        except Exception as e:
            stats["errors"].append(
                f"Error processing standing booking {sb.id} for session {session.id}: {str(e)}"
            )
            continue

    stats["materialized_count"] = stats["created_reservations"]
    stats["reservations_created"] = stats["created_reservations"]
    return stats


async def _materialize_single_standing_booking(
    db: AsyncSession,
    standing_booking: StandingBooking,
    start_date: date,
    end_date: date,
    stats: Dict[str, Any]
) -> None:
    """Materialize a single standing booking into reservations"""

    # Get the template
    template = standing_booking.template
    if not template or not template.is_active:
        return

    # Get exceptions for this standing booking
    exceptions_stmt = select(StandingBookingException).where(
        StandingBookingException.standing_booking_id == standing_booking.id
    )
    exceptions_result = await db.execute(exceptions_stmt)
    exceptions = {exc.session_date: exc for exc in exceptions_result.scalars().all()}

    # Find all class sessions for this template within the date range
    sessions_stmt = select(ClassSession).where(
        and_(
            ClassSession.template_id == template.id,
            func.date(ClassSession.start_at) >= max(start_date, standing_booking.start_date),
            func.date(ClassSession.start_at) <= min(end_date, standing_booking.end_date),
            ClassSession.status == 'scheduled'
        )
    ).order_by(ClassSession.start_at)

    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    for session in sessions:
        session_date = session.start_at.date()

        # Check if there's an exception for this date
        if session_date in exceptions:
            exception = exceptions[session_date]
            stats['skipped_exceptions'] += 1

            # If it's a reschedule, we should handle the new session
            if exception.action == 'reschedule' and exception.new_session_id:
                await _create_reservation_if_possible(
                    db, standing_booking, exception.new_session_id, stats, source='override'
                )
            continue

        # Create reservation for this session
        await _create_reservation_if_possible(
            db, standing_booking, session.id, stats, source='standing'
        )


async def _create_reservation_if_possible(
    db: AsyncSession,
    standing_booking: StandingBooking,
    session_id: int,
    stats: Dict[str, Any],
    source: str = 'standing'
) -> None:
    """Create a reservation if possible, respecting capacity and seat constraints"""

    # Check if reservation already exists (idempotency)
    existing_stmt = select(Reservation).where(
        and_(
            Reservation.session_id == session_id,
            Reservation.person_id == standing_booking.person_id
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        stats['skipped_existing'] += 1
        return

    # Get session info
    session_stmt = select(ClassSession).where(ClassSession.id == session_id)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if not session:
        return

    # Check capacity and seat availability
    if standing_booking.seat_id:
        # Class with seats (like spinning) - check if specific seat is available
        seat_check_stmt = select(Reservation).where(
            and_(
                Reservation.session_id == session_id,
                Reservation.seat_id == standing_booking.seat_id,
                Reservation.status.in_(['reserved', 'checked_in'])
            )
        )
        seat_check_result = await db.execute(seat_check_stmt)
        seat_taken = seat_check_result.scalar_one_or_none()

        if seat_taken:
            stats['skipped_seat_taken'] += 1
            return
    else:
        # Class without specific seats - check general capacity
        capacity_check_stmt = select(func.count(Reservation.id)).where(
            and_(
                Reservation.session_id == session_id,
                Reservation.status.in_(['reserved', 'checked_in'])
            )
        )
        capacity_result = await db.execute(capacity_check_stmt)
        current_reservations = capacity_result.scalar() or 0

        if current_reservations >= session.capacity:
            stats['skipped_no_capacity'] += 1
            return

    # Create the reservation
    reservation = Reservation(
        session_id=session_id,
        person_id=standing_booking.person_id,
        seat_id=standing_booking.seat_id,
        status='reserved',
        source=source
    )

    db.add(reservation)
    stats['created_reservations'] += 1


async def get_materialization_preview(
    db: AsyncSession,
    standing_booking_id: int,
    window_weeks: int = 4
) -> List[Dict[str, Any]]:
    """
    Preview what reservations would be created for a standing booking.
    Useful for showing users what their standing booking will generate.
    """
    # Get the standing booking
    sb_stmt = select(StandingBooking).options(
        joinedload(StandingBooking.template)
    ).where(StandingBooking.id == standing_booking_id)

    sb_result = await db.execute(sb_stmt)
    standing_booking = sb_result.scalar_one_or_none()

    if not standing_booking:
        return []

    template = standing_booking.template
    if not template:
        return []

    start_date = max(date.today(), standing_booking.start_date)
    end_date = min(
        start_date + timedelta(weeks=window_weeks),
        standing_booking.end_date
    )

    # Get exceptions
    exceptions_stmt = select(StandingBookingException).where(
        StandingBookingException.standing_booking_id == standing_booking_id
    )
    exceptions_result = await db.execute(exceptions_stmt)
    exceptions = {exc.session_date: exc for exc in exceptions_result.scalars().all()}

    # Find sessions
    sessions_stmt = select(ClassSession).where(
        and_(
            ClassSession.template_id == template.id,
            func.date(ClassSession.start_at) >= start_date,
            func.date(ClassSession.start_at) <= end_date,
            ClassSession.status == 'scheduled'
        )
    ).order_by(ClassSession.start_at)

    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    preview = []
    for session in sessions:
        session_date = session.start_at.date()

        # Check for exceptions
        exception = exceptions.get(session_date)
        if exception:
            if exception.action == 'skip':
                preview.append({
                    'date': session_date,
                    'session_id': session.id,
                    'session_name': session.name,
                    'start_time': session.start_at,
                    'status': 'skipped',
                    'reason': 'Exception: skip'
                })
                continue
            elif exception.action == 'reschedule':
                preview.append({
                    'date': session_date,
                    'session_id': exception.new_session_id,
                    'session_name': f"Rescheduled: {session.name}",
                    'start_time': session.start_at,
                    'status': 'rescheduled',
                    'reason': f'Rescheduled to session {exception.new_session_id}'
                })
                continue

        # Check existing reservation
        existing_stmt = select(Reservation).where(
            and_(
                Reservation.session_id == session.id,
                Reservation.person_id == standing_booking.person_id
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            preview.append({
                'date': session_date,
                'session_id': session.id,
                'session_name': session.name,
                'start_time': session.start_at,
                'status': 'existing',
                'reason': 'Reservation already exists'
            })
            continue

        # Check capacity/seat availability
        status = 'will_create'
        reason = 'Will be created'

        if standing_booking.seat_id:
            # Check seat availability
            seat_check_stmt = select(Reservation).where(
                and_(
                    Reservation.session_id == session.id,
                    Reservation.seat_id == standing_booking.seat_id,
                    Reservation.status.in_(['reserved', 'checked_in'])
                )
            )
            seat_check_result = await db.execute(seat_check_stmt)
            seat_taken = seat_check_result.scalar_one_or_none()

            if seat_taken:
                status = 'blocked'
                reason = 'Seat already taken'
        else:
            # Check capacity
            capacity_check_stmt = select(func.count(Reservation.id)).where(
                and_(
                    Reservation.session_id == session.id,
                    Reservation.status.in_(['reserved', 'checked_in'])
                )
            )
            capacity_result = await db.execute(capacity_check_stmt)
            current_reservations = capacity_result.scalar() or 0

            if current_reservations >= session.capacity:
                status = 'blocked'
                reason = 'Session at full capacity'

        preview.append({
            'date': session_date,
            'session_id': session.id,
            'session_name': session.name,
            'start_time': session.start_at,
            'status': status,
            'reason': reason
        })

    return preview
