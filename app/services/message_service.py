from sqlalchemy.orm import Session
from app.models.models import Message
from typing import List

class MessageService:
    def __init__(self, db: Session):
        self.db = db

    def add_message(self, thread_id: int, role: str, content: str) -> Message:
        msg = Message(thread_id=thread_id, role=role, content=content)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages_for_thread(self, thread_id: int) -> List[Message]:
        return self.db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()
