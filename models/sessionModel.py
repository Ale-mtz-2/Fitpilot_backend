from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgresql import Base

class User(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str]
    session: Mapped[str]
    device_name: Mapped[str]
    ip_address: Mapped[str]
    last_active: Mapped[str]
    revoked_at: Mapped[str]
    user_agent: Mapped[str]
    user_id: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    deleted_at: Mapped[str]