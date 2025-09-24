from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.postgresql import Base
# from app.models.usersModel import User

# if TYPE_CHECKING:
#     from app.models.usersModel import User

class Role(Base):
    __tablename__ = "users_roles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str]
    description: Mapped[str]
    created_at:  Mapped[Optional[datetime]] = mapped_column(
                                                    DateTime(timezone=True), 
                                                    nullable=True,
                                                    server_default=func.now()  
                                                )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
                                                    DateTime(timezone=True),                 
                                                    nullable=True,
                                                    onupdate=func.now()  
                                                    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


    users: Mapped[list["User"]] = relationship("User", back_populates="role")