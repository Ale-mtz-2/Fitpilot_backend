from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.postgresql import Base
# from app.models.roleModel import Role

# if TYPE_CHECKING:
#     from app.models.roleModel import Role

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    password: Mapped[str]
    username: Mapped[str]
    
    role_id: Mapped[int] = mapped_column(ForeignKey("users_roles.id"))

    role: Mapped["Role"] = relationship("Role", back_populates="users")