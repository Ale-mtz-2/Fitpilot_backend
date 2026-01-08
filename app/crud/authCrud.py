from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Account, People, PersonRole


async def get_account_by_username(db: AsyncSession, username: str) -> Optional[Account]:
    """Get account by username with person relationship loaded."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.person))
        .where(Account.username == username)
        .where(Account.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_person_by_account(db: AsyncSession, account_id: int) -> Optional[People]:
    """Get person associated with account."""
    result = await db.execute(
        select(People)
        .join(Account)
        .where(Account.id == account_id)
        .where(Account.is_active == True)
    )
    return result.scalar_one_or_none()


async def verify_account_credentials(db: AsyncSession, username: str, password_hash: str) -> Optional[Account]:
    """Verify account credentials."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.person))
        .where(Account.username == username)
        .where(Account.password_hash == password_hash)
        .where(Account.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_account_by_id(db: AsyncSession, account_id: int) -> Optional[Account]:
    """Get account by ID with related person and roles."""
    result = await db.execute(
        select(Account)
        .options(
            selectinload(Account.person)
            .selectinload(People.roles)
            .selectinload(PersonRole.role)
        )
        .where(Account.id == account_id)
        .where(Account.is_active == True)
    )
    return result.scalar_one_or_none()
