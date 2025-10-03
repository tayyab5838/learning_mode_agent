from sqlalchemy.orm import Session
from app.models.models import UserSession

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, agent_type: str | None = None) -> UserSession:
        """
        Create a new session for a user

        Args:
            user_id (int): user id
            agent_type (str | None, optional): Agent Name. Defaults to None.

        Returns:
            UserSession: {
            "id": int,
            "user_id": int,
            "agent_type": "string",
            "created_at": "Date"
            }
        """        
        session = UserSession(user_id=user_id, agent_type=agent_type)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session_by_id(self, session_id: int):
        return self.db.query(UserSession).filter(UserSession.id == session_id).first()

    def list_sessions_for_user(self, user_id: int):
        """
        List of all user sessions for a given user id.

        Args:
            user_id (int): user id

        Returns:
            UserSession: [
                {
                    "id": 0,
                    "user_id": 0,
                    "agent_type": "string",
                    "created_at": "2025-10-03T07:30:20.100Z"
                }
            ]
        """        
        return self.db.query(UserSession).filter(UserSession.user_id == user_id).all()
