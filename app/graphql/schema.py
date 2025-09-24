# from dataclasses import dataclass
# from fastapi import Request, Response
# from sqlalchemy.ext.asyncio import AsyncSession
# from strawberry.fastapi import BaseContext
import strawberry

# from app.auth.jwt import verify_token
# from app.crud.usersCrud import get_user_by_id
from app.graphql.auth.mutations import AuthMutation
from app.graphql.users.mutations import UserMutation
from app.graphql.users.queries import UserQuery

@strawberry.type
class Query(UserQuery):
    @strawberry.field
    def hello(self) -> str:
        return "Hello from GraphQL!"
    
@strawberry.type
class Mutation(AuthMutation, UserMutation):
    pass

# @dataclass
# class Context(BaseContext):
#     db: AsyncSession
#     request: Request
#     response: Response
#     user: object | None = None
   
schema = strawberry.Schema(query=Query, mutation=Mutation)