from fastapi import HTTPException, Request, Response
import strawberry
from user_agents import parse
import uuid

from app.auth.hashing import verify_password
from app.auth.jwt import create_access_token, create_refresh_token
from app.crud.authCrud import get_user
from app.graphql.auth.types import LoginInput, TokenResponse


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

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Credentials not valid")
        
        session_id = f"session-id{uuid.uuid4().hex}"
        # token = create_access_token({"user_id": str(user.id), "session_id": session_id})
        refresh_token = create_refresh_token({"user_id": str(user.id), "session_id": session_id})
        access_token = create_access_token({"user_id": str(user.id), "session_id": session_id})

        # user = await info.context["db"].execute(select(User))

        # user = await engine.find_one(
        #     UserModel,ACCESS_TOKEN_EXPIRE_MINUTES
        #     {
        #         "$or": [
        #             {"email": identifier},
        #             {"phone": identifier}
        #         ]
        #     }
        # )

        # print("use_in_login", user)
    
        # if not user:
        #     raise HTTPException(status_code=401, detail="User not found")

        # if not verify_password(password, user.password):
        #     raise HTTPException(status_code=401, detail="Credentials not valid")

        # session_id = f"session-id{uuid.uuid4().hex}"
        # # token = create_access_token({"user_id": str(user.id), "session_id": session_id})
        # refresh_token = create_refresh_token({"user_id": str(user.id), "session_id": session_id})
        # access_token = create_access_token({"user_id": str(user.id), "session_id": session_id})
        
        # session = SessionModel(
        #     session_id=session_id,
        #     user_id=ObjectId(user.id), 
        #     token=refresh_token, 
        #     created_at=datetime.now(),
        #     user_agent=user_agent,
        #     device_name=device_name,
        #     ip_address=ip_address,
        #     last_active_at=datetime.now(),
        #     is_active=True
        # )
        # new_session = await engine.save(session)

        # response.set_cookie(
        #     key="refresh_token",
        #     value=refresh_token,
        #     httponly=True,
        #     secure=False,             # Solo se envía en HTTPS
        #     samesite="lax",       # Previene CSRF
        #     max_age=60 * 60 * 24 * 15 # 7 días
        # )

        return TokenResponse(access_token=access_token)
        