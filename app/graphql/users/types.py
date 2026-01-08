import strawberry
from datetime import datetime
from typing import Optional, List
from app.models import People, Role, PersonRole, Account


@strawberry.type
class RoleType:
    id: int
    name: str
    code: str
    description: Optional[str] = None


@strawberry.type
class PersonRole:
    role: RoleType
    assigned_at: datetime


@strawberry.type
class Account:
    id: int
    username: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_model(cls, account: "Account") -> "Account":
        return cls(
            id=account.id,
            username=account.username,
            is_active=account.is_active,
            created_at=account.created_at
        )


@strawberry.type
class Person:
    id: int
    full_name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    wa_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    roles: List[PersonRole]

    @classmethod
    def from_model(cls, person: People) -> "Person":
        return cls(
            id=person.id,
            full_name=person.full_name,
            email=person.email,
            phone_number=person.phone_number,
            wa_id=person.wa_id,
            created_at=person.created_at,
            updated_at=person.updated_at,
            roles=[
                PersonRole(
                    role=RoleType(
                        id=pr.role.id,
                        name=pr.role.name,
                        code=pr.role.code,
                        description=pr.role.description
                    ),
                    assigned_at=pr.created_at
                )
                for pr in person.roles
            ] if person.roles else []
        )


@strawberry.input
class CreatePersonInput:
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    wa_id: Optional[str] = None


@strawberry.input
class UpdatePersonInput:
    person_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    wa_id: Optional[str] = None


@strawberry.input
class ChangePasswordInput:
    username: str
    password: str


@strawberry.type
class ChangePasswordResponse:
    message: str


@strawberry.type
class CreatePersonResponse:
    person: Person
    message: str