from typing import Union
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from strawberry.fastapi import GraphQLRouter
# from app.graphql.schema import build_context, schema, Context

from app.crud.usersCrud import list_people
from app.db.postgresql import get_db

from sqlalchemy.ext.asyncio import AsyncSession

from app.graphql.schema import schema
from app.graphql.context import build_context

# Initialize logging system
from app.core.logging_config import setup_logging, get_logger

# Initialize logging first
logger = setup_logging()
logger.info("Starting FitPilot backend application")

app = FastAPI()

# Mount static files for profile pictures
uploads_path = Path(__file__).parent.parent / "uploads"
uploads_path.mkdir(exist_ok=True)  # Ensure uploads directory exists
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
logger.info(f"Static files mounted at /uploads from {uploads_path}")

# Basic request logging middleware (helps trace login attempts)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_logger = get_logger("requests")
    response = await call_next(request)
    try:
        req_logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
    except Exception:
        pass
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"],  # Específico para desarrollo
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

graphql_app = GraphQLRouter(
    schema=schema,
    context_getter=build_context,
    graphiql=True
)
app.include_router(graphql_app, prefix="/graphql")

