import argparse
import asyncio
from collections import defaultdict
from datetime import date, datetime, time, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.orm import selectinload

from app.db.postgresql import async_session_factory
from app.models.classModel import ClassTemplate, StandingBooking
from app.models.membershipsModel import MembershipPlan, MembershipSubscription
from app.models.venueModel import Seat
from app.crud.classSessionCrud import generate_sessions_from_template
from app.crud.membershipsCrud import _align_date_to_weekday
from app.crud.standingBookingsCrud import (
    create_standing_booking,
    _materialize_single_standing_booking,
)

SPECIAL_SUBSCRIPTION_ID = 2694
SPECIAL_START_TIME = time(18, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing standing bookings and reservations for a year."
    )
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (creates/updates data).",
    )
    return parser.parse_args()


def _group_key(template: ClassTemplate) -> tuple:
    return (
        template.class_type_id,
        template.venue_id,
        template.start_time_local,
        template.instructor_id,
    )


async def _get_group_templates(
    db,
    template: ClassTemplate,
) -> list[ClassTemplate]:
    if not template or not template.is_active:
        return []

    stmt = select(ClassTemplate).where(
        and_(
            ClassTemplate.class_type_id == template.class_type_id,
            ClassTemplate.venue_id == template.venue_id,
            ClassTemplate.start_time_local == template.start_time_local,
            ClassTemplate.is_active == True,
        )
    )

    if template.instructor_id is None:
        stmt = stmt.where(ClassTemplate.instructor_id.is_(None))
    else:
        stmt = stmt.where(ClassTemplate.instructor_id == template.instructor_id)

    stmt = stmt.order_by(ClassTemplate.weekday)
    result = await db.execute(stmt)
    return result.scalars().all()


async def _find_previous_seed(
    db,
    subscription: MembershipSubscription,
) -> StandingBooking | None:
    stmt = (
        select(StandingBooking)
        .join(
            MembershipSubscription,
            StandingBooking.subscription_id == MembershipSubscription.id,
        )
        .options(selectinload(StandingBooking.template))
        .where(
            and_(
                StandingBooking.person_id == subscription.person_id,
                MembershipSubscription.id != subscription.id,
                MembershipSubscription.end_at < subscription.start_at,
            )
        )
        .order_by(
            MembershipSubscription.end_at.desc(),
            StandingBooking.created_at.desc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_templates_at_time(
    db,
    start_time: time,
) -> list[ClassTemplate]:
    stmt = select(ClassTemplate).where(
        and_(
            ClassTemplate.start_time_local == start_time,
            ClassTemplate.is_active == True,
        )
    ).order_by(
        ClassTemplate.class_type_id,
        ClassTemplate.venue_id,
        ClassTemplate.weekday,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def _get_available_seat_id(
    db,
    template: ClassTemplate,
    preferred_seat_id: int | None,
) -> tuple[int | None, bool]:
    if not template:
        return None, False

    seats_stmt = select(Seat).where(
        and_(
            Seat.venue_id == template.venue_id,
            Seat.is_active == True,
        )
    ).order_by(Seat.label)
    seats_result = await db.execute(seats_stmt)
    seats = seats_result.scalars().all()

    if not seats:
        return None, False

    taken_stmt = select(StandingBooking.seat_id).where(
        and_(
            StandingBooking.template_id == template.id,
            StandingBooking.status == "active",
            StandingBooking.seat_id.isnot(None),
        )
    )
    taken_result = await db.execute(taken_stmt)
    taken_ids = {seat_id for seat_id, in taken_result.fetchall() if seat_id}

    seat_ids = {seat.id for seat in seats}
    if preferred_seat_id and preferred_seat_id in seat_ids and preferred_seat_id not in taken_ids:
        return preferred_seat_id, True

    for seat in seats:
        if seat.id not in taken_ids:
            return seat.id, True

    return None, True


async def _cancel_previous_standing_bookings(
    db,
    *,
    person_id: int,
    template_id: int,
    subscription_id: int,
) -> int:
    stmt = (
        update(StandingBooking)
        .where(
            and_(
                StandingBooking.person_id == person_id,
                StandingBooking.template_id == template_id,
                StandingBooking.subscription_id != subscription_id,
                StandingBooking.status.in_(["active", "paused"]),
            )
        )
        .values(status="canceled")
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


async def main() -> None:
    args = parse_args()
    if not args.apply:
        print("Run with --apply to modify data.")
        return

    year_start = date(args.year, 1, 1)
    year_end = date(args.year, 12, 31)
    year_start_dt = datetime(args.year, 1, 1, tzinfo=timezone.utc)
    year_end_dt = datetime(args.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    stats = {
        "subscriptions": 0,
        "subscriptions_active": 0,
        "subscriptions_with_sb": 0,
        "subscriptions_missing_seed": 0,
        "standing_bookings_created": 0,
        "standing_bookings_reactivated": 0,
        "standing_bookings_date_aligned": 0,
        "standing_bookings_canceled": 0,
        "standing_bookings_no_seat": 0,
        "standing_bookings_conflicts": 0,
        "templates_processed": 0,
        "sessions_created": 0,
        "reservations": {
            "processed_bookings": 0,
            "created_reservations": 0,
            "skipped_no_capacity": 0,
            "skipped_seat_taken": 0,
            "skipped_existing": 0,
            "skipped_exceptions": 0,
            "errors": [],
        },
    }

    async with async_session_factory() as db:
        subs_stmt = (
            select(MembershipSubscription)
            .join(MembershipPlan, MembershipSubscription.plan_id == MembershipPlan.id)
            .options(selectinload(MembershipSubscription.plan))
            .where(
                and_(
                    MembershipPlan.fixed_time_slot == True,
                    MembershipSubscription.start_at <= year_end_dt,
                    MembershipSubscription.end_at >= year_start_dt,
                )
            )
            .order_by(MembershipSubscription.start_at)
        )

        subs_result = await db.execute(subs_stmt)
        subscriptions = subs_result.scalars().all()
        stats["subscriptions"] = len(subscriptions)

        if not subscriptions:
            print("No subscriptions found for the selected year.")
            return

        subscription_ids = [sub.id for sub in subscriptions]

        sb_stmt = (
            select(StandingBooking)
            .options(selectinload(StandingBooking.template))
            .where(StandingBooking.subscription_id.in_(subscription_ids))
        )
        sb_result = await db.execute(sb_stmt)
        standing_bookings = sb_result.scalars().all()

        sbs_by_subscription: dict[int, list[StandingBooking]] = defaultdict(list)
        for sb in standing_bookings:
            sbs_by_subscription[sb.subscription_id].append(sb)

        for idx, subscription in enumerate(subscriptions, start=1):
            touched = False
            if subscription.status == "active":
                stats["subscriptions_active"] += 1

            existing_sbs = sbs_by_subscription.get(subscription.id, [])
            if existing_sbs:
                stats["subscriptions_with_sb"] += 1

            sub_start = subscription.start_at.date()
            sub_end = subscription.end_at.date()

            if subscription.status == "active":
                for sb in existing_sbs:
                    template = sb.template
                    if not template:
                        continue

                    expected_start = _align_date_to_weekday(sub_start, template.weekday)
                    if (
                        subscription.id == SPECIAL_SUBSCRIPTION_ID
                        and template.start_time_local == SPECIAL_START_TIME
                    ):
                        expected_start = sub_start
                    expected_end = sub_end
                    if expected_start > expected_end:
                        continue

                    if sb.status != "active":
                        conflict = None
                        if sb.seat_id:
                            conflict_stmt = select(StandingBooking.id).where(
                                and_(
                                    StandingBooking.template_id == sb.template_id,
                                    StandingBooking.seat_id == sb.seat_id,
                                    StandingBooking.status == "active",
                                    StandingBooking.person_id != subscription.person_id,
                                )
                            ).limit(1)
                            conflict_result = await db.execute(conflict_stmt)
                            conflict = conflict_result.scalar_one_or_none()

                        if conflict:
                            stats["standing_bookings_conflicts"] += 1
                            continue

                        sb.status = "active"
                        stats["standing_bookings_reactivated"] += 1
                        touched = True

                    if sb.start_date != expected_start or sb.end_date != expected_end:
                        sb.start_date = expected_start
                        sb.end_date = expected_end
                        stats["standing_bookings_date_aligned"] += 1
                        touched = True

            if subscription.status != "active":
                if idx % 50 == 0:
                    print(f"Processed {idx}/{len(subscriptions)} subscriptions")
                continue

            existing_by_template = {sb.template_id: sb for sb in existing_sbs if sb.template_id}
            template_candidates: list[tuple[StandingBooking | None, ClassTemplate]] = []
            if subscription.id == SPECIAL_SUBSCRIPTION_ID:
                special_templates = await _get_templates_at_time(db, SPECIAL_START_TIME)
                for template in special_templates:
                    template_candidates.append((None, template))
            else:
                group_seeds: list[StandingBooking] = []
                if existing_sbs:
                    grouped = defaultdict(list)
                    for sb in existing_sbs:
                        if sb.template:
                            grouped[_group_key(sb.template)].append(sb)
                    for group_list in grouped.values():
                        group_seeds.append(group_list[0])
                else:
                    seed = await _find_previous_seed(db, subscription)
                    if seed:
                        group_seeds.append(seed)
                    else:
                        stats["subscriptions_missing_seed"] += 1
                        if idx % 50 == 0:
                            print(f"Processed {idx}/{len(subscriptions)} subscriptions")
                        continue

                for seed in group_seeds:
                    if not seed.template or not seed.template.is_active:
                        continue
                    group_templates = await _get_group_templates(db, seed.template)
                    for template in group_templates:
                        template_candidates.append((seed, template))

            for seed, template in template_candidates:
                if template.id in existing_by_template:
                    continue

                aligned_start = _align_date_to_weekday(sub_start, template.weekday)
                if (
                    subscription.id == SPECIAL_SUBSCRIPTION_ID
                    and template.start_time_local == SPECIAL_START_TIME
                ):
                    aligned_start = sub_start
                if aligned_start > sub_end:
                    continue

                canceled = await _cancel_previous_standing_bookings(
                    db=db,
                    person_id=subscription.person_id,
                    template_id=template.id,
                    subscription_id=subscription.id,
                )
                if canceled:
                    stats["standing_bookings_canceled"] += canceled
                    touched = True

                preferred_seat_id = seed.seat_id if seed else None
                seat_id, has_seats = await _get_available_seat_id(
                    db=db,
                    template=template,
                    preferred_seat_id=preferred_seat_id,
                )
                if has_seats and seat_id is None:
                    stats["standing_bookings_no_seat"] += 1
                    continue

                try:
                    new_sb = await create_standing_booking(
                        db=db,
                        person_id=subscription.person_id,
                        subscription_id=subscription.id,
                        template_id=template.id,
                        seat_id=seat_id,
                        start_date=aligned_start,
                        end_date=sub_end,
                    )
                    if new_sb:
                        existing_by_template[template.id] = new_sb
                        sbs_by_subscription[subscription.id].append(new_sb)
                        stats["standing_bookings_created"] += 1
                        touched = True
                except Exception as exc:  # noqa: BLE001
                    stats["reservations"]["errors"].append(
                        f"SB create failed sub={subscription.id} template={template.id}: {exc}"
                    )

            if touched:
                await db.commit()

            if idx % 50 == 0:
                print(f"Processed {idx}/{len(subscriptions)} subscriptions")

        sb_templates_stmt = (
            select(StandingBooking.template_id)
            .where(
                and_(
                    StandingBooking.subscription_id.in_(subscription_ids),
                    StandingBooking.status == "active",
                    StandingBooking.start_date <= year_end,
                    StandingBooking.end_date >= year_start,
                )
            )
            .distinct()
        )
        templates_result = await db.execute(sb_templates_stmt)
        template_ids = [row[0] for row in templates_result.fetchall() if row[0]]

        stats["templates_processed"] = len(template_ids)
        for t_index, template_id in enumerate(template_ids, start=1):
            sessions = await generate_sessions_from_template(
                db=db,
                template_id=template_id,
                start_date=year_start,
                end_date=year_end,
            )
            stats["sessions_created"] += len(sessions)
            if t_index % 50 == 0:
                print(f"Generated sessions for {t_index}/{len(template_ids)} templates")

        materialize_stmt = (
            select(StandingBooking)
            .options(selectinload(StandingBooking.template))
            .where(
                and_(
                    StandingBooking.subscription_id.in_(subscription_ids),
                    StandingBooking.status == "active",
                    StandingBooking.start_date <= year_end,
                    StandingBooking.end_date >= year_start,
                )
            )
            .order_by(StandingBooking.subscription_id)
        )
        materialize_result = await db.execute(materialize_stmt)
        materialize_sbs = materialize_result.scalars().all()

        current_sub_id = None
        for sb in materialize_sbs:
            if current_sub_id is None:
                current_sub_id = sb.subscription_id
            elif sb.subscription_id != current_sub_id:
                await db.commit()
                current_sub_id = sb.subscription_id

            stats["reservations"]["processed_bookings"] += 1
            try:
                await _materialize_single_standing_booking(
                    db=db,
                    standing_booking=sb,
                    start_date=year_start,
                    end_date=year_end,
                    stats=stats["reservations"],
                )
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                stats["reservations"]["errors"].append(
                    f"Materialize failed sb={sb.id}: {exc}"
                )

        await db.commit()

    stats["reservations"]["materialized_count"] = stats["reservations"]["created_reservations"]
    stats["reservations"]["reservations_created"] = stats["reservations"]["created_reservations"]

    print("=== 2026 Generation Summary ===")
    print(f"Subscriptions considered: {stats['subscriptions']}")
    print(f"Active subscriptions: {stats['subscriptions_active']}")
    print(f"Subscriptions with standing bookings: {stats['subscriptions_with_sb']}")
    print(f"Subscriptions missing seed: {stats['subscriptions_missing_seed']}")
    print(f"Standing bookings created: {stats['standing_bookings_created']}")
    print(f"Standing bookings reactivated: {stats['standing_bookings_reactivated']}")
    print(f"Standing bookings date aligned: {stats['standing_bookings_date_aligned']}")
    print(f"Standing bookings canceled: {stats['standing_bookings_canceled']}")
    print(f"Standing bookings without seat: {stats['standing_bookings_no_seat']}")
    print(f"Standing booking conflicts: {stats['standing_bookings_conflicts']}")
    print(f"Templates processed: {stats['templates_processed']}")
    print(f"Sessions created: {stats['sessions_created']}")
    print("Reservations materialized:")
    for key in [
        "processed_bookings",
        "created_reservations",
        "skipped_no_capacity",
        "skipped_seat_taken",
        "skipped_existing",
        "skipped_exceptions",
    ]:
        print(f"  {key}: {stats['reservations'][key]}")
    if stats["reservations"]["errors"]:
        print(f"Errors: {len(stats['reservations']['errors'])}")


if __name__ == "__main__":
    asyncio.run(main())
