import strawberry


@strawberry.type
class RoleType:
    id: int
    role: str
    description: str | None = None

@strawberry.type
class User:
    id: str
    username: str
    role_id: int
    role: RoleType

@strawberry.input
class ChangePasswordInput:
    username: str
    password: str

@strawberry.type
class ChangePasswordResponse:
    message: str

