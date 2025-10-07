from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Message
from typing import List

class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(self, thread_id: int, role: str, content: str) -> Message:
        """
        Add a message to a thread.
        """        
        new_message = Message(thread_id=thread_id, role=role, content=content)
        self.db.add(new_message)
        await self.db.commit()
        await self.db.refresh(new_message)
        return new_message

    async def get_messages_for_thread(self, thread_id: int) -> List[Message]:
        """
        Retrieve all messages for a thread.
        """
        stmt = select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
        result = await self.db.execute(stmt)
        return result.scalars().all()