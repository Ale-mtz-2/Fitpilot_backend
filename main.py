from typing import Union

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema, Context

from app.crud.usersCrud import list_users
from app.db.postgresql import get_db

from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

async def get_context(db: AsyncSession = Depends(get_db)) -> Context:
    return Context(db=db)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/users")
async def read_users(db: AsyncSession = Depends(get_db)):
    return await list_users(db=db)