import strawberry


@strawberry.type
class User:
    id: str
    username: str
    password: str
    role_id: int

@strawberry.input
class ChangePasswordInput:
    username: str
    password: str

@strawberry.type
class ChangePasswordResponse:
    message: str

