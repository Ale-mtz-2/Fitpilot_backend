import strawberry

from app.auth.hashing import hash_password
from app.crud.usersCrud import update_password
from app.graphql.users.types import ChangePasswordInput, ChangePasswordResponse


@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def change_password(self, data: ChangePasswordInput, info: strawberry.Info) -> ChangePasswordResponse:
        password = data.password
        username = data.username

        hashed_password = hash_password(password=password)

        result_update_user = await update_password(db=info.context.db, username=username, password=hashed_password)
        print("result_update_user",result_update_user)

        return ChangePasswordResponse(message="Password updated")
        # await info.context.db.execute(
        #     "UPDATE users SET password = :hashed_password WHERE username = :username",
        #     {"hashed_password": hashed_password, "username": username},
        # )