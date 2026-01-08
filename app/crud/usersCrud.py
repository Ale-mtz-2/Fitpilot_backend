from typing import Optional
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.conversions import coerce_int
from app.models import People, Account, PersonRole, Role

async def get_person_by_id(db: AsyncSession, person_id: int) -> Optional[People]:
    """Get person by ID with roles loaded"""
    person_id = coerce_int(person_id)
    if person_id is None:
        return None

    result = await db.execute(
        select(People)
        .options(selectinload(People.roles).selectinload(PersonRole.role))
        .where(People.id == person_id)
        .where(People.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

async def get_account_by_person_id(db: AsyncSession, person_id: int) -> Optional[Account]:
    """Get account for a specific person"""
    person_id = coerce_int(person_id)
    if person_id is None:
        return None

    result = await db.execute(
        select(Account)
        .where(Account.person_id == person_id)
        .where(Account.is_active == True)
    )
    return result.scalar_one_or_none()

async def list_people(db: AsyncSession, role_code: str = None):
    """List all people, optionally filtered by role"""
    query = select(People).options(
        selectinload(People.roles).selectinload(PersonRole.role)
    ).where(People.deleted_at.is_(None))

    if role_code:
        query = query.join(PersonRole).join(Role).where(Role.code == role_code)

    result = await db.execute(query)
    return result.scalars().all()

async def list_members(db: AsyncSession):
    """List all people with member role"""
    return await list_people(db, role_code='member')

async def update_account_password(db: AsyncSession, username: str, password_hash: str) -> Optional[Account]:
    """Update account password"""
    stmt = (
        update(Account)
        .where(Account.username == username)
        .where(Account.is_active == True)
        .values(password_hash=password_hash)
        .returning(Account.id, Account.username, Account.person_id)
    )

    result = await db.execute(stmt)
    row = result.first()
    await db.commit()
    return row

async def get_person_roles(db: AsyncSession, person_id: int):
    """Get all roles for a person"""
    person_id = coerce_int(person_id)
    if person_id is None:
        return []

    result = await db.execute(
        select(Role)
        .join(PersonRole)
        .where(PersonRole.person_id == person_id)
    )
    return result.scalars().all()

async def create_person(db: AsyncSession, full_name: str, email: str = None, phone_number: str = None) -> People:
    """Create a new person"""
    person = People(
        full_name=full_name,
        email=email,
        phone_number=phone_number
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person
