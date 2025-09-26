from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import INET
from app.db.postgresql import Base



class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    refresh_token: Mapped[str]
    session: Mapped[str]
    device_name: Mapped[str] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True),nullable=True)
    user_agent: Mapped[str] = mapped_column(nullable=True)
    user_id: Mapped[int] = mapped_column(nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
                                                    TIMESTAMP(timezone=True), 
                                                    nullable=True,
                                                    server_default=func.now()  
                                                )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
                                                    TIMESTAMP(timezone=True),                 
                                                    nullable=True,
                                                    onupdate=func.now()  
                                                    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
                                                    TIMESTAMP(timezone=True),
                                                    nullable=True)