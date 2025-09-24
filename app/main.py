from typing import Union

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
# from app.graphql.schema import build_context, schema, Context

from app.crud.usersCrud import list_users
from app.db.postgresql import get_db

from sqlalchemy.ext.asyncio import AsyncSession

from app.graphql.schema import schema
from app.graphql.context import build_context

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

graphql_app = GraphQLRouter(
    schema=schema,
    context_getter=build_context,
    graphiql=True
)
app.include_router(graphql_app, prefix="/graphql")
