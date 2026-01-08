"""
Lead management and marketing models for FitPilot
Based on the leads playbook and modern schema with English naming
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    DateTime, ForeignKey, Integer, BigInteger, String, Boolean, Text, JSON,
    CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from app.db.postgresql import Base

if TYPE_CHECKING:
    from app.models.userModel import People, Account
    from app.models.membershipsModel import MembershipSubscription


class LeadSource(Base):
    """Lead sources catalog (WhatsApp, landing pages, referrals, etc.)"""

    __tablename__ = "lead_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    leads: Mapped[List["Lead"]] = relationship(back_populates="source")


class Lead(Base):
    """Lead management with funnel status tracking"""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lead_sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    score: Mapped[Optional[int]] = mapped_column(Integer)
    owner_account_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("accounts.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    converted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Legacy migration fields
    legacy_id: Mapped[Optional[int]] = mapped_column(Integer)
    migrated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    person: Mapped["People"] = relationship()
    source: Mapped["LeadSource"] = relationship(back_populates="leads")
    owner: Mapped[Optional["Account"]] = relationship()
    events: Mapped[List["LeadEvent"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    attributions: Mapped[List["LeadAttribution"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','contacted','qualified','converted','lost','disqualified')",
            name="ck_lead_status"
        ),
        # Prevent duplicate ACTIVE leads per person + source
        Index(
            "uq_lead_active_per_source",
            "person_id", "source_id",
            unique=True,
            postgresql_where="status IN ('new','contacted','qualified')"
        ),
        Index("idx_leads_person_status", "person_id", "status"),
        Index("idx_leads_source_created", "source_id", "created_at"),
        Index("idx_leads_status_updated", "status", "updated_at"),
        Index("idx_leads_legacy_id", "legacy_id", postgresql_where="legacy_id IS NOT NULL"),
    )


class LeadEvent(Base):
    """Lead interaction events and touchpoints"""

    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lead_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("accounts.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="events")
    creator: Mapped[Optional["Account"]] = relationship()

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('message_in','message_out','form_submit','status_change','reservation','payment_attempt','note','migration')",
            name="ck_lead_event_type"
        ),
        Index("idx_lead_events_lead_at", "lead_id", "event_at"),
        Index("idx_lead_events_type", "event_type", "event_at"),
    )


class FormSubmission(Base):
    """Form submissions from landing pages and web forms"""

    __tablename__ = "form_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    form_id: Mapped[Optional[str]] = mapped_column(String(80))
    form_name: Mapped[Optional[str]] = mapped_column(String(120))
    submitted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    landing_url: Mapped[Optional[str]] = mapped_column(Text)
    referrer_url: Mapped[Optional[str]] = mapped_column(Text)
    utm_source: Mapped[Optional[str]] = mapped_column(String(80))
    utm_medium: Mapped[Optional[str]] = mapped_column(String(80))
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120))
    utm_term: Mapped[Optional[str]] = mapped_column(String(120))
    utm_content: Mapped[Optional[str]] = mapped_column(String(120))
    gclid: Mapped[Optional[str]] = mapped_column(String(200))
    fbclid: Mapped[Optional[str]] = mapped_column(String(200))
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    person: Mapped["People"] = relationship()

    # Indexes
    __table_args__ = (
        Index("idx_form_submissions_person", "person_id", "submitted_at"),
        Index("idx_form_submissions_campaign", "utm_campaign", "submitted_at"),
        Index("idx_form_submissions_source", "utm_source", "submitted_at"),
    )


class MarketingCampaign(Base):
    """Marketing campaigns for advanced attribution reporting"""

    __tablename__ = "marketing_campaigns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    platform: Mapped[Optional[str]] = mapped_column(String(30))  # 'meta','google','tiktok','email'
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    channel: Mapped[Optional[str]] = mapped_column(String(30))  # 'ads','email','organic','referral'
    external_id: Mapped[Optional[str]] = mapped_column(String(120))
    start_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    end_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    attributions: Mapped[List["LeadAttribution"]] = relationship(back_populates="campaign")

    # Indexes
    __table_args__ = (
        Index("idx_campaigns_platform_dates", "platform", "start_at", "end_at"),
        Index("idx_campaigns_external_id", "external_id", postgresql_where="external_id IS NOT NULL"),
    )


class LeadAttribution(Base):
    """Multi-touch attribution for leads to campaigns"""

    __tablename__ = "lead_attributions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lead_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("marketing_campaigns.id"))
    utm_source: Mapped[Optional[str]] = mapped_column(String(80))
    utm_medium: Mapped[Optional[str]] = mapped_column(String(80))
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120))
    utm_term: Mapped[Optional[str]] = mapped_column(String(120))
    utm_content: Mapped[Optional[str]] = mapped_column(String(120))
    landing_url: Mapped[Optional[str]] = mapped_column(Text)
    click_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    referrer_url: Mapped[Optional[str]] = mapped_column(Text)
    gclid: Mapped[Optional[str]] = mapped_column(String(200))
    fbclid: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="attributions")
    campaign: Mapped[Optional["MarketingCampaign"]] = relationship(back_populates="attributions")

    # Indexes
    __table_args__ = (
        Index("idx_lead_attr_lead", "lead_id"),
        Index("idx_lead_attr_campaign", "campaign_id"),
        Index("idx_lead_attr_utm", "utm_source", "utm_medium", "utm_campaign"),
    )


class CommunicationOptIn(Base):
    """Communication consent management per channel"""

    __tablename__ = "communications_opt_in"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    source: Mapped[Optional[str]] = mapped_column(String(80))  # 'form','whatsapp','manual','import'
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB)  # checkbox capture, IP, message_id, etc.
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    person: Mapped["People"] = relationship()

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "channel IN ('whatsapp','email','sms')",
            name="ck_communication_channel"
        ),
        Index("idx_optin_person_channel", "person_id", "channel"),
        Index("idx_optin_active", "channel", "granted_at", postgresql_where="revoked_at IS NULL"),
    )


class WhatsAppThread(Base):
    """WhatsApp conversation summary per person"""

    __tablename__ = "whatsapp_threads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    wa_id: Mapped[Optional[str]] = mapped_column(String(100))
    phone_e164: Mapped[Optional[str]] = mapped_column(String(32))
    last_inbound_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    last_outbound_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    last_message_snippet: Mapped[Optional[str]] = mapped_column(Text)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provider: Mapped[Optional[str]] = mapped_column(String(40))  # 'meta','twilio','360dialog', etc.
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    person: Mapped["People"] = relationship()

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_wa_thread_person"),
        Index("idx_wa_threads_wa_id", "wa_id", postgresql_where="wa_id IS NOT NULL"),
        Index("idx_wa_threads_phone", "phone_e164", postgresql_where="phone_e164 IS NOT NULL"),
        Index("idx_wa_threads_last_activity", "last_inbound_at", "last_outbound_at"),
    )