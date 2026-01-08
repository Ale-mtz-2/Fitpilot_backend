from typing import List, Optional

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.membershipsCrud import (
    get_membership_plans, get_membership_plan_by_id,
    get_active_subscriptions, get_expiring_subscriptions, get_membership_subscriptions
)
from app.graphql.memberships.types import MembershipPlan, Subscription
from app.graphql.auth.permissions import IsAuthenticated
from app.core.conversions import coerce_int


@strawberry.type
class MembershipsQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    async def membership_plans(self, info) -> List[MembershipPlan]:
        """Get all available membership plans"""
        db: AsyncSession = info.context.db
        plans_data = await get_membership_plans(db=db)
        return [MembershipPlan.from_data(plan_data) for plan_data in plans_data]

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def membership_plan(self, info, plan_id: int) -> Optional[MembershipPlan]:
        """Get membership plan by ID"""
        db: AsyncSession = info.context.db

        plan_id = coerce_int(plan_id)
        if plan_id is None:
            return None

        plan_data = await get_membership_plan_by_id(db=db, plan_id=plan_id)
        return MembershipPlan.from_data(plan_data) if plan_data else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def active_subscriptions(self, info, limit: int = 100) -> List[Subscription]:
        """Get list of active subscriptions"""
        db: AsyncSession = info.context.db
        subscriptions_data = await get_active_subscriptions(db=db, limit=limit)
        return [Subscription.from_data(sub_data) for sub_data in subscriptions_data]

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def expiring_subscriptions(self, info, days_ahead: int = 7) -> List[Subscription]:
        """Get subscriptions expiring in the next N days"""
        db: AsyncSession = info.context.db
        subscriptions_data = await get_expiring_subscriptions(db=db, days_ahead=days_ahead)
        return [Subscription.from_data(sub_data) for sub_data in subscriptions_data]

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def membership_subscriptions(
        self,
        info,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Subscription]:
        """Get membership subscriptions with optional filters"""
        db: AsyncSession = info.context.db
        subscriptions_data = await get_membership_subscriptions(
            db=db,
            limit=limit,
            offset=offset,
            status=status,
            search=search
        )
        return [Subscription.from_data(sub_data) for sub_data in subscriptions_data]
