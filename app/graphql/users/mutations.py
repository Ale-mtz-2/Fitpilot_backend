import strawberry
from fastapi import HTTPException

from app.security.hashing import hash_password
from app.crud.usersCrud import update_account_password, create_person
from app.graphql.users.types import (
    ChangePasswordInput, ChangePasswordResponse,
    CreatePersonInput, CreatePersonResponse, Person
)


@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def change_password(self, data: ChangePasswordInput, info: strawberry.Info) -> ChangePasswordResponse:
        password = data.password
        username = data.username

        hashed_password = hash_password(password=password)

        result = await update_account_password(
            db=info.context.db,
            username=username,
            password_hash=hashed_password
        )

        if not result:
            raise HTTPException(status_code=404, detail="Account not found")

        return ChangePasswordResponse(message="Password updated successfully")

    @strawberry.mutation
    async def create_person(self, data: CreatePersonInput, info: strawberry.Info) -> CreatePersonResponse:
        """Create a new person in the system"""
        person = await create_person(
            db=info.context.db,
            full_name=data.full_name,
            email=data.email,
            phone_number=data.phone_number
        )

        return CreatePersonResponse(
            person=Person.from_model(person),
            message="Person created successfully"
        )