from datetime import datetime
from typing import Optional
import strawberry


@strawberry.type
class SessionInfo:
    """Información de sesión de usuario."""
    id: int
    session_id: str
    device_name: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    last_active_at: Optional[datetime]
    created_at: Optional[datetime]
    revoked_at: Optional[datetime]
    is_current: bool = False  # Indica si es la sesión actual

    @staticmethod
    def from_model(session, current_session_id: Optional[str] = None):
        """Convierte un modelo Session a SessionInfo."""
        return SessionInfo(
            id=session.id,
            session_id=session.session,
            device_name=session.device_name,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            last_active_at=session.last_active_at,
            created_at=session.created_at,
            revoked_at=session.revoked_at,
            is_current=(session.session == current_session_id) if current_session_id else False
        )


@strawberry.input
class RevokeSessionInput:
    """Input para revocar una sesión."""
    session_id: str
