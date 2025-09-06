from datetime import datetime
from typing import Optional
import strawberry

@strawberry.input
class LoginInput:
    identifier: str
    password: str

# @strawberry.input
# class RefreshTokenInput:
#     token: str

@strawberry.type
class RefreshTokenResponse:
    access_token: str

@strawberry.type
class TokenResponse:
    access_token: str