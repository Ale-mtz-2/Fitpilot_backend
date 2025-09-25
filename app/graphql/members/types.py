from datetime import datetime
from typing import Optional, List

import strawberry

from app.crud.membersCrud import (
    LatestMembersData,
    MembersData,
    PersonaData,
    MembershipData,
)


@strawberry.type
class PersonaType:
    id: int
    nombre_origen: Optional[str]
    telefono: str
    wa_id: Optional[str]

    @staticmethod
    def from_dataclass(data: PersonaData) -> "PersonaType":
        return PersonaType(
            id=data.id,
            nombre_origen=data.nombre_origen,
            telefono=data.telefono,
            wa_id=data.wa_id,
        )


@strawberry.type
class MembershipType:
    id: Optional[int]
    nombre: Optional[str]
    duracion: Optional[int]
    tipo_duracion: Optional[str]
    precio: Optional[float]

    @staticmethod
    def from_dataclass(data: Optional[MembershipData]) -> Optional["MembershipType"]:
        if data is None:
            return None
        return MembershipType(
            id=data.id,
            nombre=data.nombre,
            duracion=data.duracion,
            tipo_duracion=data.tipo_duracion,
            precio=data.precio,
        )


@strawberry.type
class LatestMembersType:
    pago_id: Optional[int]
    fecha_pago: Optional[datetime]
    fecha_fin: Optional[datetime]
    estado: str
    status: Optional[str]
    paquete: Optional[MembershipType]

    @staticmethod
    def from_dataclass(data: Optional[LatestMembersData]) -> Optional["LatestMembersType"]:
        if data is None:
            return None
        return LatestMembersType(
            pago_id=data.pago_id,
            fecha_pago=data.fecha_pago,
            fecha_fin=data.fecha_fin,
            estado=data.estado,
            status=data.status,
            paquete=MembershipType.from_dataclass(data.paquete),
        )


@strawberry.type
class MembersType:
    id: int
    persona_id: int
    fecha_registro: datetime
    email: Optional[str]
    consent_promos: int
    consent_record: int
    persona: PersonaType
    ultima_membresia: Optional[LatestMembersType]

    @staticmethod
    def from_dataclass(data: MembersData) -> "MembersType":
        return MembersType(
            id=data.id,
            persona_id=data.persona_id,
            fecha_registro=data.fecha_registro,
            email=data.email,
            consent_promos=data.consent_promos,
            consent_record=data.consent_record,
            persona=PersonaType.from_dataclass(data.persona),
            ultima_membresia=LatestMembersType.from_dataclass(data.ultima_membresia),
        )


@strawberry.type
class MembersConnection:
    items: List[MembersType]
    total: int

    @staticmethod
    def from_collection(items: List[MembersData], total: int) -> "MembersConnection":
        return MembersConnection(
            items=[MembersType.from_dataclass(item) for item in items],
            total=total,
        )
