from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgresql import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    password: Mapped[str]
    username: Mapped[str]
    role_id: Mapped[int]
