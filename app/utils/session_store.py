from sqlalchemy.orm import Session

from app.models.session_models import User, UserSession, Thread, Message
from app.auth_utils import hash_password, verify_password, create_access_token
from app.schemas import UserCreate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, user_data: UserCreate):
        # Check if username OR email already exists
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        if existing_user:
            return None  # user already exists

        hashed_pw = hash_password(user_data.password)
        user = User(username=user_data.username, email=user_data.email, password=hashed_pw)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str):
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password):
            return None
        return user

    def create_token(self, user: User):
        return create_access_token({"sub": user.username})


# -------- Session Service --------
class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def start_session(self, user_id: int):
        session = UserSession(user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session


# -------- Thread Service --------
class ThreadService:
    def __init__(self, db: Session):
        self.db = db

    def create_thread(self, session_id: int, title: str | None = None):
        thread = Thread(session_id=session_id, title=title)
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def get_threads_by_session(self, session_id: int):
        return self.db.query(Thread).filter(Thread.session_id == session_id).all()

    def get_thread_by_id(self, thread_id: int):
        return self.db.query(Thread).filter(Thread.id == thread_id).first()


# -------- Message Service --------
class MessageService:
    def __init__(self, db: Session):
        self.db = db

    def save_message(self, thread_id: int, role: str, content: str):
        message = Message(thread_id=thread_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(self, thread_id: int):
        return self.db.query(Message).filter(Message.thread_id == thread_id).all()
