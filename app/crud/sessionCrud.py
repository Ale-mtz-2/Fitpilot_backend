
from sqlalchemy import func, select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
import datetime

from app.models.sessionModel import Session


async def create_session(db: AsyncSession, sessionEntry: Session) -> None:
    # session = Session(sessionEntry)
    db.add(sessionEntry)
    await db.commit()


# async def update_session(db: AsyncSession, sessionEntry: Session) -> None:
    # stmt = update(Session).where(Session.id == sessionEntry.id).values(**sessionEntry.dict())
    # await db.execute(stmt)
    # await db.commit()

async def verify_session(db: AsyncSession, session_id: str) -> Session | None:
    res = await db.execute(select(Session).where(Session.session == session_id))
    return res.scalar_one_or_none()

async def update_last_active_at(db: AsyncSession, session_id: str) -> None:
    print("session_id in update_last_active_at", session_id)
    stmt = update(Session).where(Session.session == session_id).values(last_active_at=func.now())
    await db.execute(stmt)
    await db.commit()