from sqlalchemy.orm import Session
from app.models.models import Thread

class ThreadService:
    def __init__(self, db: Session):
        self.db = db

    def create_thread(self, session_id: int, title: str | None = None) -> Thread:
        thread = Thread(session_id=session_id, title=title)
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def get_thread_by_id(self, thread_id: int):
        return self.db.query(Thread).filter(Thread.id == thread_id).first()

    def list_threads_for_session(self, session_id: int):
        return self.db.query(Thread).filter(Thread.session_id == session_id).all()
