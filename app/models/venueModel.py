"""
Venue and equipment management models for FitPilot
Based on the modern schema with English naming
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    DateTime, Date, ForeignKey, Integer, BigInteger, Numeric, String, Text,
    Boolean, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import TIMESTAMP

from app.db.postgresql import Base

if TYPE_CHECKING:
    from app.models.classModel import ClassTemplate, ClassSession, Reservation


class Venue(Base):
    """Physical venues/rooms"""

    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    seats: Mapped[List["Seat"]] = relationship(back_populates="venue")
    class_templates: Mapped[List["ClassTemplate"]] = relationship(back_populates="venue")
    class_sessions: Mapped[List["ClassSession"]] = relationship(back_populates="venue")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_venue_capacity"),
    )


class SeatType(Base):
    """Types of seats/equipment positions"""

    __tablename__ = "seat_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    seats: Mapped[List["Seat"]] = relationship(back_populates="seat_type")


class Seat(Base):
    """Individual seats/positions in venues"""

    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venue_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    row_number: Mapped[Optional[int]] = mapped_column(Integer)
    col_number: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    seat_type_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("seat_types.id"))

    # Relationships
    venue: Mapped["Venue"] = relationship(back_populates="seats")
    seat_type: Mapped[Optional["SeatType"]] = relationship(back_populates="seats")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="seat")
    asset_assignments: Mapped[List["AssetSeatAssignment"]] = relationship(back_populates="seat")

    __table_args__ = (
        UniqueConstraint("venue_id", "label", name="uq_venue_seat_label"),
    )


class AssetType(Base):
    """Types of equipment/assets"""

    __tablename__ = "asset_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    asset_models: Mapped[List["AssetModel"]] = relationship(back_populates="asset_type")


class AssetModel(Base):
    """Specific models of equipment"""

    __tablename__ = "asset_models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("asset_types.id"), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(80))
    model_name: Mapped[Optional[str]] = mapped_column(String(120))
    maintenance_interval_days: Mapped[Optional[int]] = mapped_column(Integer)
    maintenance_interval_classes: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    asset_type: Mapped["AssetType"] = relationship(back_populates="asset_models")
    assets: Mapped[List["Asset"]] = relationship(back_populates="asset_model")


class Asset(Base):
    """Individual pieces of equipment"""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("asset_models.id"), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(120), unique=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_service")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    retired_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    asset_model: Mapped["AssetModel"] = relationship(back_populates="assets")
    seat_assignments: Mapped[List["AssetSeatAssignment"]] = relationship(back_populates="asset")
    events: Mapped[List["AssetEvent"]] = relationship(back_populates="asset")

    __table_args__ = (
        CheckConstraint("status IN ('in_service','maintenance','retired')", name="ck_asset_status"),
        Index("idx_assets_status", "status", "asset_model_id"),
    )


class AssetSeatAssignment(Base):
    """Assignment of assets to seats with history"""

    __tablename__ = "asset_seat_assignments"

    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, primary_key=True)
    seat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False)
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="seat_assignments")
    seat: Mapped["Seat"] = relationship(back_populates="asset_assignments")

    __table_args__ = (
        CheckConstraint("unassigned_at IS NULL OR unassigned_at > assigned_at", name="ck_assignment_dates"),
        Index("uq_asset_active_assignment", "asset_id", unique=True, postgresql_where="unassigned_at IS NULL"),
        Index("uq_seat_active_asset", "seat_id", unique=True, postgresql_where="unassigned_at IS NULL"),
    )


class AssetEvent(Base):
    """Maintenance and other events for assets"""

    __tablename__ = "asset_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("accounts.id"))

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint("event_type IN ('maintenance','repair','inspection','incident')", name="ck_event_type"),
        Index("idx_asset_events_asset", "asset_id", "performed_at"),
    )