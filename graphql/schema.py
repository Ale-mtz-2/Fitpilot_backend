from dataclasses import dataclass
import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import BaseContext

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


class Context(BaseContext):
    def __init__(self, db):
        super().__init__()
        self.db = db

schema = strawberry.Schema(query=Query, mutation=Mutation)