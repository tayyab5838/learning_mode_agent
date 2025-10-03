# app/services/session_service.py
from sqlalchemy.orm import Session
from app.models.models import UserSession

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, agent_type: str | None = None) -> UserSession:
        session = UserSession(user_id=user_id, agent_type=agent_type)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session_by_id(self, session_id: int):
        return self.db.query(UserSession).filter(UserSession.id == session_id).first()

    def list_sessions_for_user(self, user_id: int):
        return self.db.query(UserSession).filter(UserSession.user_id == user_id).all()
