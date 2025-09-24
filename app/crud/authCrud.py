from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usersModel import User

async def get_user(db: AsyncSession, username: str) -> User | None: 
    print("username",username)
    res = await db.execute(select(User).where(User.username == username))
    print("res_get_user",res)
    return res.scalar_one_or_none()


