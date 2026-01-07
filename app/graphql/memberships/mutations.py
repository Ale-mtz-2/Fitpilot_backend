from datetime import datetime, timezone

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.membershipsCrud import (
    create_membership_plan,
    create_membership_subscription,
    get_membership_plan_by_id,
    create_member_enrollment,
    SubscriptionData
)
from app.crud.membersCrud import get_member_by_id
from app.graphql.memberships.types import (
    CreateMembershipPlanInput, CreateSubscriptionInput,
    CreateMemberEnrollmentInput,
    MembershipPlanResponse, SubscriptionResponse,
    MemberEnrollmentResponse,
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
            return MembershipPlanResponse(
                plan=None,
                message=f"Error al crear plan de membresÃ­a: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_subscription(self, info, input: CreateSubscriptionInput) -> SubscriptionResponse:
        """Create a new membership subscription"""
        db: AsyncSession = info.context.db

        try:
            created_by = getattr(info.context, 'user_id', None)

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

            return SubscriptionResponse(
                subscription=Subscription.from_data(subscription_data),
                message="Suscripci\u00f3n creada exitosamente"
            )

        except Exception as e:
            return SubscriptionResponse(
                subscription=None,
                message=f"Error al crear suscripci\u00f3n: {str(e)}"
            )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    async def create_member_enrollment(self, info, input: CreateMemberEnrollmentInput) -> MemberEnrollmentResponse:
        """Create member, subscription and payment in one step."""
        db: AsyncSession = info.context.db

        try:
            created_by = getattr(info.context, 'user_id', None)

            person, subscription, payment, plan = await create_member_enrollment(
                db=db,
                full_name=input.full_name,
                email=input.email,
                phone_number=input.phone_number,
                wa_id=input.wa_id,
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

            return MemberEnrollmentResponse(
                member=Member.from_data(member_data) if member_data else None,
                subscription=Subscription.from_data(subscription_data),
                payment=PaymentRecord.from_model(payment),
                message="Suscripci\u00f3n creada exitosamente"
            )

        except Exception as e:
            return MemberEnrollmentResponse(
                member=None,
                subscription=None,
                payment=None,
                message=f"Error al crear suscripci\u00f3n: {str(e)}"
            )



