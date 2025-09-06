from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usersModel import User

# def create_user(db: Session, name: str) -> User:
#     u = User(name=name)
#     db.add(u)
#     db.commit()
#     db.refresh(u)
#     return u

async def list_users(db: AsyncSession):
    res = await db.execute(select(User))
    return res.scalars().all()

async def update_password(db: AsyncSession, username: str, password: str) -> User:
    print("username",username)
    print("password",password)
    stmt = (
        update(User)
        .where(User.username == username)
        .values(password=password)
        .returning(User.id, User.username)   # columnas que quieras devolver
    )

    res = await db.execute(stmt)
    row = res.first()   # None si no actualizó nada
    await db.commit()
    return row 
