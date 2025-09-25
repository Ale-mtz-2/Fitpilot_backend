from fastapi import HTTPException, Request, Response
import strawberry
from user_agents import parse
import uuid
import datetime

from app.auth.hashing import verify_password
from app.auth.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.crud.authCrud import get_user
from app.crud.sessionCrud import create_session
from app.graphql.auth.types import LoginInput, TokenResponse
from app.models.sessionModel import Session


@strawberry.type
class AuthMutation:
    @strawberry.mutation
    async def login(self, data: LoginInput, info: strawberry.Info) -> TokenResponse:

        # get information from request
        request: Request = info.context.request
        user_agent = request.headers.get("user-agent")
        response: Response = info.context.response

        
        
        ip_address = request.client.host
        ua = parse(user_agent)
        device_name = f"{ua.device.family} - {ua.os.family} {ua.os.version_string}"
        # -----------------------------
        
        identifier = data.identifier
        password = data.password

        user = await get_user(db=info.context.db, username=identifier)
        print("user",user)
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Credentials not valid")
        
        session_id = f"session-id{uuid.uuid4().hex}"
        # token = create_access_token({"user_id": str(user.id), "session_id": session_id})
        refresh_token = create_refresh_token({"user_id": str(user.id), "username": user.username , "session_id": session_id })
        access_token = create_access_token({"user_id": str(user.id), "username": user.username , "session_id": session_id})
    
        payload_refresh = verify_refresh_token(refresh_token)
        exp = datetime.datetime.fromtimestamp(payload_refresh.get("exp")) 

        print("exp--->", exp)

        session = Session(
            refresh_token = refresh_token,
            session = session_id,
            device_name = device_name,
            ip_address = ip_address,
            user_agent = user_agent,
            user_id = user.id,
            revoked_at = exp,
            last_active_at = datetime.datetime.now()
        )
        print("session",session)

        insert_session = await create_session(
            db=info.context.db, 
            sessionEntry=session
        )

        print("insert_session", insert_session)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,             # Solo se envía en HTTPS
            samesite="lax",       # Previene CSRF
            max_age=60 * 60 * 24 * 15 # 7 días
        )

        response.headers["x-access-token"] = access_token

        return TokenResponse(access_token=access_token)
        