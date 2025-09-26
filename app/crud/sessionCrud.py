
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sessionModel import Session


async def create_session(db: AsyncSession, sessionEntry: Session) -> Session:
    """Creates a new session with proper error handling."""
    db.add(sessionEntry)
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise

    await db.refresh(sessionEntry)
    return sessionEntry


async def verify_session(db: AsyncSession, session_id: str) -> Session | None:
    """Verifies if a session exists and returns it."""
    res = await db.execute(select(Session).where(Session.session == session_id))
    return res.scalar_one_or_none()


async def update_last_active_at(db: AsyncSession, session_id: str) -> None:
    """Updates the last_active_at timestamp for a session using database function."""
    print("session_id in update_last_active_at", session_id)
    stmt = update(Session).where(Session.session == session_id).values(last_active_at=func.now())
    try:
        await db.execute(stmt)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def touch_session(db: AsyncSession, session_id: str) -> None:
    """Updates the last_active_at timestamp for a session with explicit UTC time."""
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            update(Session)
            .where(Session.session == session_id)
            .values(last_active_at=timestamp, updated_at=datetime.utcnow())
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def revoke_session(db: AsyncSession, session_id: str) -> None:
    """Marks the session as revoked."""
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            update(Session)
            .where(Session.session == session_id)
            .values(revoked_at=timestamp, updated_at=datetime.utcnow())
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise


async def update_refresh_token(db: AsyncSession, session_id: str, refresh_token: str) -> None:
    """Stores a new refresh token for an existing session."""
    try:
        await db.execute(
            update(Session)
            .where(Session.session == session_id)
            .values(refresh_token=refresh_token, updated_at=datetime.utcnow())
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise