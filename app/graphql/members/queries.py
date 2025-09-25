from typing import Optional

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.membersCrud import list_members
from app.graphql.members.types import MembersConnection


@strawberry.type
class MembersQuery:
    @strawberry.field
    async def members(
        self,
        info,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> MembersConnection:
        db: AsyncSession = info.context.db
        result = await list_members(
            db=db,
            limit=limit,
            offset=offset,
            search=search,
        )
        return MembersConnection.from_collection(
            result["items"],
            result["total"],
        )

