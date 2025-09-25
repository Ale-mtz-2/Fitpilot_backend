from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usersModel import User
from sqlalchemy.orm import selectinload

# def create_user(db: Session, name: str) -> User:
#     u = User(name=name)
#     db.add(u)
#     db.commit()
#     db.refresh(u)
#     return u

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    user_id = int(user_id)
    print("user_id-->get_user_by_id: ", type(user_id))
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()

async def list_users(db: AsyncSession):
    res = await db.execute(
            select(User).options(selectinload(User.role))
        )
    return res.scalars().all()

async def update_password(db: AsyncSession, username: str, password: str) -> User:
    print("username",username)
    print("password",password)
    stmt = (
        update(User)
        .where(User.username == username)
        .values(password=password)
        .returning(User.id, User.username)
    )

    res = await db.execute(stmt)
    row = res.first()   # None si no actualizó nada
    await db.commit()
    return row 
