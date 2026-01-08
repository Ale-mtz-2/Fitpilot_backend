from datetime import datetime
from typing import Optional

import strawberry
from app.crud.membershipsCrud import MembershipPlanData, SubscriptionData
from app.models.membershipsModel import Payment as PaymentModel
from app.graphql.members.types import Member


@strawberry.type
class MembershipPlan:
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

    @classmethod
    def from_data(cls, data: MembershipPlanData) -> "MembershipPlan":
        return cls(
            id=data.id,
            name=data.name,
            description=data.description,
            price=data.price,
            duration_value=data.duration_value,
            duration_unit=data.duration_unit,
            class_limit=data.class_limit,
            fixed_time_slot=data.fixed_time_slot,
            max_sessions_per_day=data.max_sessions_per_day,
            max_sessions_per_week=data.max_sessions_per_week,
            created_at=data.created_at
        )


@strawberry.type
class Subscription:
    id: int
    person_id: int
    plan_id: int
    start_at: datetime
    end_at: datetime
    status: str
    plan_name: str
    person_name: str
    remaining_days: Optional[int]

    @classmethod
    def from_data(cls, data: SubscriptionData) -> "Subscription":
        return cls(
            id=data.id,
            person_id=data.person_id,
            plan_id=data.plan_id,
            start_at=data.start_at,
            end_at=data.end_at,
            status=data.status,
            plan_name=data.plan_name,
            person_name=data.person_name,
            remaining_days=data.remaining_days
        )


@strawberry.type
class PaymentRecord:
    id: int
    person_id: int
    subscription_id: Optional[int]
    amount: float
    method: str
    status: str
    paid_at: datetime
    provider: Optional[str]
    provider_payment_id: Optional[str]
    external_reference: Optional[str]
    comment: Optional[str]
    recorded_by: Optional[int]

    @classmethod
    def from_model(cls, payment: PaymentModel) -> "PaymentRecord":
        return cls(
            id=payment.id,
            person_id=payment.person_id,
            subscription_id=payment.subscription_id,
            amount=float(payment.amount),
            method=payment.method,
            status=payment.status,
            paid_at=payment.paid_at,
            provider=payment.provider,
            provider_payment_id=payment.provider_payment_id,
            external_reference=payment.external_reference,
            comment=payment.comment,
            recorded_by=payment.recorded_by
        )


@strawberry.input
class CreateMembershipPlanInput:
    name: str
    price: float
    duration_value: int
    duration_unit: str
    description: Optional[str] = None
    class_limit: Optional[int] = None
    fixed_time_slot: bool = False
    max_sessions_per_day: Optional[int] = None
    max_sessions_per_week: Optional[int] = None


@strawberry.input
class CreateSubscriptionInput:
    person_id: int
    plan_id: int
    start_at: Optional[datetime] = None


@strawberry.input
class CreateMemberEnrollmentInput:
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None  # WhatsApp number goes here
    plan_id: int
    start_at: Optional[datetime] = None
    payment_method: str = 'cash'
    payment_amount: Optional[float] = None
    payment_status: str = 'COMPLETED'
    payment_comment: Optional[str] = None
    payment_provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    external_reference: Optional[str] = None
    # Optional: standing booking details (to mimic renewal flow)
    template_id: Optional[int] = None
    seat_id: Optional[int] = None


@strawberry.input
class RenewSubscriptionInput:
    member_id: int
    plan_id: int
    template_id: Optional[int] = None
    seat_id: Optional[int] = None
    start_at: Optional[datetime] = None
    payment_method: str = 'cash'
    payment_amount: Optional[float] = None
    payment_status: str = 'COMPLETED'
    payment_comment: Optional[str] = None
    payment_provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    external_reference: Optional[str] = None


@strawberry.type
class MembershipPlanResponse:
    plan: Optional[MembershipPlan]
    message: str


@strawberry.type
class SubscriptionResponse:
    subscription: Optional[Subscription]
    message: str

@strawberry.type
class MemberEnrollmentResponse:
    member: Optional[Member]
    subscription: Optional[Subscription]
    payment: Optional[PaymentRecord]
    message: str
    standingBookingId: Optional[int] = None
    materializationStats: Optional[str] = None


@strawberry.type
class SubscriptionRenewalResponse:
    subscription: Optional[Subscription]
    payment: Optional[PaymentRecord]
    message: str
    standingBookingId: Optional[int] = None
    materializationStats: Optional[str] = None

