from __future__ import annotations

from typing import Optional

import strawberry

from app.auth.jwt import verify_token
from app.crud.authCrud import get_user_by_id
from app.graphql.auth.types import AuthUser, to_auth_user


def _extract_bearer_token(info: strawberry.Info) -> Optional[str]:
    authorization = info.context.request.headers.get("authorization", "")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


@strawberry.type
class AuthQuery:
    @strawberry.field
    async def current_user(self, info: strawberry.Info) -> Optional[AuthUser]:
        token = _extract_bearer_token(info)
        if not token:
            return None

        payload = verify_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        user = await get_user_by_id(db=info.context.db, user_id=int(user_id))
        if not user:
            return None

        return to_auth_user(user)
