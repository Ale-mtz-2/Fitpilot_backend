import app.models  # 🔥 importa todo de __init__.py
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    "postgresql+asyncpg://appuser:secret123@localhost:5432/defaultdb",
    echo=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    metadata = MetaData(schema="app")
    pass

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session