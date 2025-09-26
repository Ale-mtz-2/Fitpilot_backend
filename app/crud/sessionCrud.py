
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sessionModel import Session


async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    session_id: str,
    refresh_token: str,
    device_name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """Creates a new session for the given user with proper error handling."""
    last_active = datetime.now(timezone.utc)
    session_row = Session(
        user_id=user_id,
        session=session_id,
        refresh_token=refresh_token,
        device_name=device_name,
        ip_address=ip_address,
        user_agent=user_agent,
        last_active_at=last_active,
    )

    db.add(session_row)
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise

    await db.refresh(session_row)
    return session_row


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