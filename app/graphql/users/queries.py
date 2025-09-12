from fastapi import Depends
import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.usersCrud import list_users
from app.db.postgresql import get_db
from app.graphql.users.types import User


@strawberry.type
class UserQuery:
    @strawberry.field
    async def users(self, info) -> list[User]:
        db = info.context.db

        users = await list_users(db=db)
        return users
        # return await info.context["db"].execute(select(User))