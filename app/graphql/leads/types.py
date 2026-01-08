from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

import strawberry
from app.graphql.users.types import Person
from app.graphql.members.types import MembershipInfo


@strawberry.type
class LeadSource:
    id: int
    code: str
    name: str
    created_at: datetime


@strawberry.enum
class LeadStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"
    DISQUALIFIED = "disqualified"


@strawberry.enum
class LeadEventType(Enum):
    MESSAGE_IN = "message_in"
    MESSAGE_OUT = "message_out"
    FORM_SUBMIT = "form_submit"
    STATUS_CHANGE = "status_change"
    RESERVATION = "reservation"
    PAYMENT_ATTEMPT = "payment_attempt"
    NOTE = "note"
    MIGRATION = "migration"


@strawberry.enum
class CommunicationChannel(Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"



@strawberry.type
class LeadEvent:
    id: int
    event_type: LeadEventType
    event_at: datetime
    notes: Optional[str]
    payload: Optional[strawberry.scalars.JSON]
    created_at: datetime


@strawberry.type
class Lead:
    id: int
    person: Person
    source: LeadSource
    status: LeadStatus
    score: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    converted_at: Optional[datetime]
    legacy_id: Optional[int]

    # Related data
    events: List[LeadEvent] = strawberry.field(default_factory=list)
    latest_event: Optional[LeadEvent] = None


@strawberry.type
class FormSubmission:
    id: int
    person: Person
    form_id: Optional[str]
    form_name: Optional[str]
    submitted_at: datetime
    landing_url: Optional[str]
    referrer_url: Optional[str]
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    utm_term: Optional[str]
    utm_content: Optional[str]
    gclid: Optional[str]
    fbclid: Optional[str]
    payload: Optional[strawberry.scalars.JSON]


@strawberry.type
class CommunicationOptIn:
    id: int
    person: Person
    channel: CommunicationChannel
    granted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    source: Optional[str]
    evidence: Optional[strawberry.scalars.JSON]


@strawberry.type
class WhatsAppThread:
    id: int
    person: Person
    wa_id: Optional[str]
    phone_e164: Optional[str]
    last_inbound_at: Optional[datetime]
    last_outbound_at: Optional[datetime]
    last_message_snippet: Optional[str]
    is_open: bool
    provider: Optional[str]


@strawberry.type
class LeadStats:
    """Lead funnel statistics"""
    total_leads: int
    new_leads: int
    contacted_leads: int
    qualified_leads: int
    converted_leads: int
    lost_leads: int
    conversion_rate: float
    by_source: List["LeadSourceStats"]


@strawberry.type
class LeadSourceStats:
    source: LeadSource
    count: int
    conversion_rate: float
    latest_lead_at: Optional[datetime]


# Input types for mutations
@strawberry.input
class CreateLeadInput:
    person_id: Optional[int] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    wa_id: Optional[str] = None
    source_code: str
    notes: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


@strawberry.input
class UpdateLeadInput:
    lead_id: int
    status: Optional[LeadStatus] = None
    score: Optional[int] = None
    notes: Optional[str] = None
    owner_account_id: Optional[int] = None


@strawberry.input
class AddLeadEventInput:
    lead_id: int
    event_type: LeadEventType
    notes: Optional[str] = None
    payload: Optional[strawberry.scalars.JSON] = None


@strawberry.input
class CreateFormSubmissionInput:
    person_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    form_id: Optional[str] = None
    form_name: Optional[str] = None
    landing_url: Optional[str] = None
    referrer_url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    gclid: Optional[str] = None
    fbclid: Optional[str] = None
    payload: Optional[strawberry.scalars.JSON] = None


@strawberry.input
class WhatsAppLeadInput:
    wa_id: Optional[str] = None
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    message_snippet: Optional[str] = None
    provider: Optional[str] = None


@strawberry.input
class LeadFilters:
    status: Optional[List[LeadStatus]] = None
    source_codes: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_phone: Optional[bool] = None
    has_email: Optional[bool] = None
    converted_only: Optional[bool] = None


@strawberry.input
class LeadPagination:
    page: int = 1
    per_page: int = 20
    order_by: str = "created_at"
    order_direction: str = "DESC"


# Response types
@strawberry.type
class LeadResponse:
    lead: Lead
    message: str


@strawberry.type
class LeadsPageResponse:
    leads: List[Lead]
    total: int
    page: int
    per_page: int
    total_pages: int


@strawberry.type
class FormSubmissionResponse:
    submission: FormSubmission
    lead: Optional[Lead]
    message: str


@strawberry.type
class LeadConversionResponse:
    lead: Lead
    subscription: Optional[MembershipInfo]
    message: str