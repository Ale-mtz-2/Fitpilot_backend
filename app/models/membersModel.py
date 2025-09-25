from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class Persona(Base):
    """Person record linked to gym members."""

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telefono: Mapped[str] = mapped_column(String(255))
    nombre_origen: Mapped[Optional[str]] = mapped_column(String(255))
    wa_id: Mapped[Optional[str]] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    members: Mapped[list["Members"]] = relationship(back_populates="persona")


class Membership(Base):
    """Membership or package purchased by members."""

    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    duracion: Mapped[Optional[int]] = mapped_column(Integer)
    tipo_duracion: Mapped[Optional[str]] = mapped_column(String(50))

    pagos: Mapped[list["Payment"]] = relationship(back_populates="paquete")


class Members(Base):
    """Gym members entry."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("app.personas.id"), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    consent_promos: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    consent_record: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    persona: Mapped[Persona] = relationship(back_populates="members")
    pagos: Mapped[list["Payment"]] = relationship(back_populates="member")


class Payment(Base):
    """Payments performed by members."""

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_member: Mapped[int] = mapped_column(ForeignKey("app.members.id"), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    id_membership: Mapped[int] = mapped_column(ForeignKey("app.memberships.id"), nullable=False)
    tipo_pago: Mapped[str] = mapped_column(String(50), nullable=False)
    comentario: Mapped[Optional[str]] = mapped_column(Text)
    mp_payment_id: Mapped[Optional[str]] = mapped_column(String(50))
    external_reference: Mapped[Optional[str]] = mapped_column(String(100))
    webhook_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[Optional[str]] = mapped_column(String(20), default="COMPLETED")

    member: Mapped[Members] = relationship(back_populates="pagos")
    paquete: Mapped[Membership] = relationship(back_populates="pagos")


