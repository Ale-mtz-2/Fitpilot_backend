from dataclasses import dataclass
import datetime
from strawberry.fastapi import BaseContext
from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, verify_refresh_token, verify_token
from app.crud.sessionCrud import update_last_active_at, verify_session
from app.crud.usersCrud import get_user_by_id
from app.db.postgresql import get_db


@dataclass
class Context(BaseContext):
    db: AsyncSession
    request: Request
    response: Response
    user: object | None = None
    

async def build_context(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Context:
    refresh_token = request.cookies.get("refresh_token")

    user = None
    new_access_token = None

    # access_token = request.headers.get("Authorization").split(" ")[1]
    access_token = request.headers.get("x-access-token")
    print("access_token",access_token)
    print("refresh_token_1st",refresh_token)

    if access_token:
        payload = verify_token(access_token)
        print("payload__access",payload)
        if payload:
            user_id = payload.get("user_id")
            if user_id:
                user = await get_user_by_id(db, user_id)
        else:
            # user = None
            if refresh_token:
                payload_refresh = verify_refresh_token(refresh_token)
                if payload_refresh is None:
                    return Context(db=db, request=request, response=response, user=None)
                session_id = str(payload_refresh.get("session_id"))
                verified_session = await verify_session(db, session_id)
                print("verified_session",verified_session.id)
                if((verified_session and verified_session.deleted_at != None)):
                    user = None
                    print("session deleted")
                    print("session_id-->",session_id)
                    print("refresh_token",refresh_token)
                    return Context(db=db, request=request, response=response, user=user)
                else:
                    user_id = payload_refresh.get("user_id")
                    if user_id:
                        user = await get_user_by_id(db, user_id)
                        print("payload__refresh",payload_refresh)
                        # new_access_token = create_access_token({"user_id": user_id})
                        new_access_token = create_access_token({"user_id": user_id, "username": payload_refresh.get('username') , "session_id": payload_refresh.get('session_id')})
                        print('session_id------->',session_id)
                        response_update_last_active = await update_last_active_at(db,session_id)
                        response.headers["x-access-token"] = new_access_token


    return Context(db=db, request=request, response=response, user=user)
