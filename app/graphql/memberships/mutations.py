from datetime import datetime, timezone

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.membershipsCrud import (
    create_membership_plan,
    create_membership_subscription,
    get_membership_plan_by_id,
    create_member_enrollment,
    create_member_enrollment_with_standing_booking,
    renew_subscription_with_standing_booking,
    SubscriptionData
)
from app.crud.membersCrud import get_member_by_id
from app.graphql.memberships.types import (
    CreateMembershipPlanInput, CreateSubscriptionInput,
    CreateMemberEnrollmentInput, RenewSubscriptionInput,
    MembershipPlanResponse, SubscriptionResponse,
    MemberEnrollmentResponse, SubscriptionRenewalResponse,
    MembershipPlan, Subscription, PaymentRecord
)
from app.graphql.members.types import Member
from app.graphql.auth.permissions import IsAuthenticated


@strawberry.type
class MembershipMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_membership_plan(self, info, input: CreateMembershipPlanInput) -> MembershipPlanResponse:
        """Create a new membership plan"""
        db: AsyncSession = info.context.db

        try:
            plan = await create_membership_plan(
                db=db,
                name=input.name,
                price=input.price,
                duration_value=input.duration_value,
                duration_unit=input.duration_unit,
                description=input.description,
                class_limit=input.class_limit,
                fixed_time_slot=input.fixed_time_slot,
                max_sessions_per_day=input.max_sessions_per_day,
                max_sessions_per_week=input.max_sessions_per_week
            )

            # Get plan data
            plan_data = await get_membership_plan_by_id(db=db, plan_id=plan.id)

            return MembershipPlanResponse(
                plan=MembershipPlan.from_data(plan_data) if plan_data else None,
                message="Plan de membresÃ­a creado exitosamente"
            )

        except Exception as e:
            # Rollback in case of error
            await db.rollback()
            return MembershipPlanResponse(
                plan=None,
                message=f"Error al crear plan de membresÃ­a: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_subscription(self, info, input: CreateSubscriptionInput) -> SubscriptionResponse:
        """Create a new membership subscription"""
        db: AsyncSession = info.context.db

        try:
            created_by = getattr(info.context, 'account_id', None)

            subscription = await create_membership_subscription(
                db=db,
                person_id=input.person_id,
                plan_id=input.plan_id,
                start_at=input.start_at,
                created_by=created_by
            )

            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(subscription.__class__)
                .options(
                    selectinload(subscription.__class__.person),
                    selectinload(subscription.__class__.plan)
                )
                .where(subscription.__class__.id == subscription.id)
            )
            sub_with_relations = result.scalar_one()

            subscription_data = SubscriptionData(
                id=sub_with_relations.id,
                person_id=sub_with_relations.person_id,
                plan_id=sub_with_relations.plan_id,
                start_at=sub_with_relations.start_at,
                end_at=sub_with_relations.end_at,
                status=sub_with_relations.status,
                plan_name=sub_with_relations.plan.name,
                person_name=sub_with_relations.person.full_name or "Sin nombre",
                remaining_days=(sub_with_relations.end_at - sub_with_relations.start_at).days
            )

            # Ensure transaction is committed
            await db.commit()

            return SubscriptionResponse(
                subscription=Subscription.from_data(subscription_data),
                message="Suscripci\u00f3n creada exitosamente"
            )

        except Exception as e:
            # Rollback in case of error
            await db.rollback()
            return SubscriptionResponse(
                subscription=None,
                message=f"Error al crear suscripci\u00f3n: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_member_enrollment(self, info, input: CreateMemberEnrollmentInput) -> MemberEnrollmentResponse:
        """Create member, subscription and payment; optionally create standing bookings + sessions like renewal."""
        db: AsyncSession = info.context.db

        try:
            created_by = getattr(info.context, 'account_id', None)

            if getattr(input, 'template_id', None):
                person, subscription, payment, plan, standing_booking_id, materialization_stats = (
                    await create_member_enrollment_with_standing_booking(
                        db=db,
                        full_name=input.full_name,
                        email=input.email,
                        phone_number=input.phone_number,  # WhatsApp number stored here
                        plan_id=input.plan_id,
                        start_at=input.start_at,
                        payment_method=input.payment_method,
                        payment_amount=input.payment_amount,
                        payment_status=input.payment_status,
                        payment_comment=input.payment_comment,
                        payment_provider=input.payment_provider,
                        provider_payment_id=input.provider_payment_id,
                        external_reference=input.external_reference,
                        recorded_by=created_by,
                        template_id=input.template_id,
                        seat_id=getattr(input, 'seat_id', None),
                        auto_materialize=True,
                    )
                )
            else:
                person, subscription, payment, plan = await create_member_enrollment(
                    db=db,
                    full_name=input.full_name,
                    email=input.email,
                    phone_number=input.phone_number,  # WhatsApp number stored here
                    plan_id=input.plan_id,
                    start_at=input.start_at,
                    payment_method=input.payment_method,
                    payment_amount=input.payment_amount,
                    payment_status=input.payment_status,
                    payment_comment=input.payment_comment,
                    payment_provider=input.payment_provider,
                    provider_payment_id=input.provider_payment_id,
                    external_reference=input.external_reference,
                    recorded_by=created_by
                )

            member_data = await get_member_by_id(db=db, member_id=person.id)

            now = datetime.now(timezone.utc)
            remaining_days = (subscription.end_at - now).days if subscription.end_at > now else 0

            subscription_data = SubscriptionData(
                id=subscription.id,
                person_id=subscription.person_id,
                plan_id=subscription.plan_id,
                start_at=subscription.start_at,
                end_at=subscription.end_at,
                status=subscription.status,
                plan_name=plan.name,
                person_name=person.full_name or "Sin nombre",
                remaining_days=remaining_days
            )

            # Commit the transaction after all operations
            await db.commit()

            # Build message and top-level fields like renewal
            try:
                import json
                message_payload = {"text": "Suscripci\u00f3n creada exitosamente"}
                if 'materialization_stats' in locals() and isinstance(materialization_stats, dict):
                    message_payload["standingBookingIds"] = materialization_stats.get("standing_booking_ids", [])
                    message_payload["materializationStats"] = materialization_stats
                if 'standing_booking_id' in locals():
                    message_payload["standingBookingId"] = standing_booking_id
                message_text = json.dumps(message_payload)
            except Exception:
                message_text = "Suscripci\u00f3n creada exitosamente"

            return MemberEnrollmentResponse(
                member=Member.from_data(member_data) if member_data else None,
                subscription=Subscription.from_data(subscription_data),
                payment=PaymentRecord.from_model(payment),
                message=message_text,
                standingBookingId=standing_booking_id if 'standing_booking_id' in locals() else None,
                materializationStats=(json.dumps(materialization_stats) if 'materialization_stats' in locals() and materialization_stats is not None else None),
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating member enrollment: {str(e)}", exc_info=True)

            # Roll back the transaction explicitly
            await db.rollback()

            return MemberEnrollmentResponse(
                member=None,
                subscription=None,
                payment=None,
                message=f"Error al crear suscripci\u00f3n: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def renew_subscription(self, info, input: RenewSubscriptionInput) -> SubscriptionRenewalResponse:
        """Renew a member's subscription."""
        db: AsyncSession = info.context.db

        try:
            created_by = getattr(info.context, 'account_id', None)

            # Log the input for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Renewing subscription for member {input.member_id}, plan {input.plan_id}")

            subscription, payment, plan, standing_booking_id, materialization_stats = await renew_subscription_with_standing_booking(
                db=db,
                member_id=input.member_id,
                plan_id=input.plan_id,
                template_id=input.template_id,
                seat_id=input.seat_id,
                start_at=input.start_at,
                payment_method=input.payment_method,
                payment_amount=input.payment_amount,
                payment_status=input.payment_status,
                payment_comment=input.payment_comment,
                payment_provider=input.payment_provider,
                provider_payment_id=input.provider_payment_id,
                external_reference=input.external_reference,
                recorded_by=created_by
            )

            # Log results based on what was created
            if standing_booking_id:
                logger.info(f"Successfully created subscription {subscription.id}, payment {payment.id}, and standing booking {standing_booking_id}")
                logger.info(f"Materialization stats: {materialization_stats}")
            else:
                logger.info(f"Successfully created subscription {subscription.id} and payment {payment.id} (no standing booking required)")

            # Ensure the transaction is committed before returning
            await db.commit()

            # Calculate remaining days for response
            now = datetime.now(timezone.utc)
            remaining_days = (subscription.end_at - now).days if subscription.end_at > now else 0

            subscription_data = SubscriptionData(
                id=subscription.id,
                person_id=subscription.person_id,
                plan_id=subscription.plan_id,
                start_at=subscription.start_at,
                end_at=subscription.end_at,
                status=subscription.status,
                plan_name=plan.name,
                person_name="", # Will be populated from member data if needed
                remaining_days=remaining_days
            )

            # Prepare response message with standing booking info embedded as JSON
            import json
            response_data = {
                "text": "Suscripción renovada exitosamente",
                "standingBookingId": standing_booking_id,  # Backward compatibility: first ID
                "standingBookingIds": materialization_stats.get("standing_booking_ids", []),  # NEW: all IDs
                "materializationStats": materialization_stats
            }
            message_with_data = json.dumps(response_data)

            return SubscriptionRenewalResponse(
                subscription=Subscription.from_data(subscription_data),
                payment=PaymentRecord.from_model(payment),
                message=message_with_data
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error renewing subscription: {str(e)}", exc_info=True)

            await db.rollback()

            return SubscriptionRenewalResponse(
                subscription=None,
                payment=None,
                message=f"Error al renovar suscripción: {str(e)}"
            )