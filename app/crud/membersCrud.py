from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membersModel import Members, Payment, Persona, Membership


@dataclass
class PersonaData:
    id: int
    nombre_origen: Optional[str]
    telefono: str
    wa_id: Optional[str]


@dataclass
class MembershipData:
    id: Optional[int]
    nombre: Optional[str]
    duracion: Optional[int]
    tipo_duracion: Optional[str]
    precio: Optional[float]


@dataclass
class LatestMembersData:
    pago_id: Optional[int]
    fecha_pago: Optional[datetime]
    fecha_fin: Optional[datetime]
    estado: str
    status: Optional[str]
    paquete: Optional[MembershipData]


@dataclass
class MembersData:
    id: int
    persona_id: int
    fecha_registro: datetime
    email: Optional[str]
    consent_promos: int
    consent_record: int
    persona: PersonaData
    ultima_membresia: Optional[LatestMembersData]


def _calculate_end_date(
    fecha_pago: Optional[datetime],
    duracion: Optional[int],
    tipo_duracion: Optional[str]
) -> Optional[datetime]:
    if not fecha_pago or not duracion or not tipo_duracion:
        return None

    tipo = tipo_duracion.lower().replace("\u00f1", "n")
    if tipo.startswith("dia"):
        return fecha_pago + timedelta(days=duracion)
    if tipo.startswith("sem"):
        return fecha_pago + timedelta(weeks=duracion)
    if tipo.startswith("mes"):
        # Approximation: one month equals 30 days
        return fecha_pago + timedelta(days=30 * duracion)
    if tipo.startswith("ano") or tipo.startswith("an"):
        return fecha_pago + timedelta(days=365 * duracion)

    return None


def _determine_status(
    fecha_fin: Optional[datetime],
    payment_status: Optional[str],
    membership: Optional[MembershipData]
) -> str:
    if fecha_fin:
        return "Activo" if fecha_fin >= datetime.utcnow() else "Vencido"

    if payment_status:
        if payment_status.upper() == "COMPLETED":
            return "Activo"
        return payment_status.capitalize()

    if membership:
        return "En revision"

    return "Sin datos"


async def list_members(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Obtiene la lista de socios con su ultima membresia conocida."""

    payments_subquery = (
        select(
            Payment.id.label("payment_id"),
            Payment.id_member.label("member_id"),
            Payment.fecha_pago.label("fecha_pago"),
            Payment.status.label("payment_status"),
            Payment.id_membership.label("membership_id"),
            Membership.nombre.label("membership_nombre"),
            Membership.duracion.label("membership_duracion"),
            Membership.tipo_duracion.label("membership_tipo"),
            Membership.precio.label("membership_precio"),
            func.row_number()
            .over(
                partition_by=Payment.id_member,
                order_by=Payment.fecha_pago.desc()
            )
            .label("rn"),
        )
        .join(Membership, Membership.id == Payment.id_membership, isouter=True)
        .subquery()
    )

    count_stmt = select(func.count()).select_from(Members).join(Persona)

    if search:
        search_term = f"%{search.lower()}%"
        count_stmt = count_stmt.where(
            or_(
                func.lower(Persona.nombre_origen).like(search_term),
                func.lower(Persona.telefono).like(search_term),
                func.lower(Members.email).like(search_term),
            )
        )

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    data_stmt = (
        select(
            Members.id.label("members_id"),
            Members.persona_id.label("members_persona_id"),
            Members.fecha_registro.label("fecha_registro"),
            Members.email.label("email"),
            Members.consent_promos.label("consent_promos"),
            Members.consent_record.label("consent_record"),
            Persona.id.label("persona_id"),
            Persona.nombre_origen.label("persona_nombre"),
            Persona.telefono.label("persona_telefono"),
            Persona.wa_id.label("persona_wa_id"),
            payments_subquery.c.payment_id,
            payments_subquery.c.fecha_pago,
            payments_subquery.c.payment_status,
            payments_subquery.c.membership_id,
            payments_subquery.c.membership_nombre,
            payments_subquery.c.membership_duracion,
            payments_subquery.c.membership_tipo,
            payments_subquery.c.membership_precio,
        )
        .join(Persona, Persona.id == Members.persona_id)
        .join(
            payments_subquery,
            payments_subquery.c.member_id == Members.id,
            isouter=True,
        )
        .where(
            or_(
                payments_subquery.c.rn == 1,
                payments_subquery.c.rn.is_(None),
            )
        )
    )

    if search:
        search_term = f"%{search.lower()}%"
        data_stmt = data_stmt.where(
            or_(
                func.lower(Persona.nombre_origen).like(search_term),
                func.lower(Persona.telefono).like(search_term),
                func.lower(Members.email).like(search_term),
            )
        )

    data_stmt = (
        data_stmt.order_by(
            func.lower(Persona.nombre_origen).asc(),
            Members.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(data_stmt)
    rows = result.mappings().all()

    items: list[MembersData] = []

    for row in rows:
        membership_info = None
        if row["membership_id"] is not None or row["membership_nombre"] is not None:
            membership_price = row["membership_precio"]
            membership_info = MembershipData(
                id=row["membership_id"],
                nombre=row["membership_nombre"],
                duracion=row["membership_duracion"],
                tipo_duracion=row["membership_tipo"],
                precio=float(membership_price) if membership_price is not None else None,
            )

        fecha_fin = _calculate_end_date(
            row["fecha_pago"],
            row["membership_duracion"],
            row["membership_tipo"],
        )

        estado = _determine_status(fecha_fin, row["payment_status"], membership_info)

        latest = None
        if any(
            row.get(key) is not None
            for key in ("payment_id", "fecha_pago", "payment_status", "membership_id", "membership_nombre")
        ):
            latest = LatestMembersData(
                pago_id=row["payment_id"],
                fecha_pago=row["fecha_pago"],
                fecha_fin=fecha_fin,
                estado=estado,
                status=row["payment_status"],
                paquete=membership_info,
            )

        persona = PersonaData(
            id=row["persona_id"],
            nombre_origen=row["persona_nombre"],
            telefono=row["persona_telefono"],
            wa_id=row["persona_wa_id"],
        )

        items.append(
            MembersData(
                id=row["members_id"],
                persona_id=row["members_persona_id"],
                fecha_registro=row["fecha_registro"],
                email=row["email"],
                consent_promos=row["consent_promos"],
                consent_record=row["consent_record"],
                persona=persona,
                ultima_membresia=latest,
            )
        )

    return {"items": items, "total": total}








