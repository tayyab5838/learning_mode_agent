from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import logging

from app.models.models import Message

logger = logging.getLogger(__name__)


# Custom Exceptions
class MessageCreationError(Exception):
    """Raised when message creation fails"""
    pass


class MessageNotFoundError(Exception):
    """Raised when message is not found"""
    pass


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self, 
        thread_id: int, 
        role: str, 
        content: str
    ) -> Message:
        """
        Add a message to a thread.
        
        Args:
            thread_id: ID of the thread
            role: Message role ('user' or 'assistant')
            content: Message content
            
        Returns:
            Created message
            
        Raises:
            MessageCreationError: If message creation fails
        """
        try:
            message = Message(
                thread_id=thread_id,
                role=role,
                content=content
            )
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            
            logger.info(
                f"Message created: ID={message.id}, Thread={thread_id}, "
                f"Role={role}, Content length={len(content)}"
            )
            return message
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                f"Database integrity error creating message: {str(e)}"
            )
            raise MessageCreationError(
                "Failed to create message due to database constraint. "
                "Thread may not exist."
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Unexpected error creating message: {str(e)}", 
                exc_info=True
            )
            raise MessageCreationError("Failed to create message")

    async def get_messages_for_thread(
        self, 
        thread_id: int
    ) -> list[Message]:
        """
        Get all messages for a thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            List of messages ordered by creation time (oldest first)
        """
        try:
            stmt = (
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at.asc())  # Chronological order
            )
            result = await self.db.execute(stmt)
            messages = result.scalars().all()
            
            logger.info(
                f"Retrieved {len(messages)} messages for thread {thread_id}"
            )
            return list(messages)
            
        except Exception as e:
            logger.error(
                f"Error retrieving messages for thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def get_message_by_id(self, message_id: int) -> Message:
        """
        Get a message by its ID.
        
        Args:
            message_id: ID of the message
            
        Returns:
            Message object
            
        Raises:
            MessageNotFoundError: If message doesn't exist
        """
        try:
            stmt = select(Message).where(Message.id == message_id)
            result = await self.db.execute(stmt)
            message = result.scalar_one_or_none()
            
            if not message:
                logger.warning(f"Message not found: ID={message_id}")
                raise MessageNotFoundError(
                    f"Message with ID {message_id} not found"
                )
            
            return message
            
        except MessageNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving message {message_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def delete_message(self, message_id: int) -> None:
        """
        Delete a message.
        
        Args:
            message_id: ID of the message to delete
            
        Raises:
            MessageNotFoundError: If message doesn't exist
        """
        try:
            message = await self.get_message_by_id(message_id)
            
            await self.db.delete(message)
            await self.db.commit()
            
            logger.info(f"Message deleted: ID={message_id}")
            
        except MessageNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error deleting message {message_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def get_message_count_for_thread(self, thread_id: int) -> int:
        """
        Get the number of messages in a thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Number of messages
        """
        try:
            messages = await self.get_messages_for_thread(thread_id)
            return len(messages)
        except Exception as e:
            logger.error(
                f"Error counting messages for thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def get_conversation_context(
        self, 
        thread_id: int, 
        limit: int | None = None
    ) -> list[dict]:
        """
        Get conversation context formatted for LLM.
        
        Args:
            thread_id: ID of the thread
            limit: Optional limit on number of recent messages to retrieve
            
        Returns:
            List of messages in format: [{"role": "user", "content": "..."}, ...]
        """
        try:
            messages = await self.get_messages_for_thread(thread_id)
            
            # Apply limit if specified (get most recent messages)
            if limit is not None and len(messages) > limit:
                messages = messages[-limit:]
            
            context = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            logger.info(
                f"Generated conversation context for thread {thread_id}: "
                f"{len(context)} messages"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Error generating conversation context: {str(e)}", 
                exc_info=True
            )
            raise

    async def update_message_content(
        self, 
        message_id: int, 
        new_content: str
    ) -> Message:
        """
        Update message content (for editing).
        
        Args:
            message_id: ID of the message
            new_content: New content
            
        Returns:
            Updated message
            
        Raises:
            MessageNotFoundError: If message doesn't exist
        """
        try:
            message = await self.get_message_by_id(message_id)
            
            old_content = message.content
            message.content = new_content
            
            await self.db.commit()
            await self.db.refresh(message)
            
            logger.info(
                f"Message updated: ID={message_id}, "
                f"Old length={len(old_content)}, New length={len(new_content)}"
            )
            return message
            
        except MessageNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error updating message {message_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def delete_messages_for_thread(self, thread_id: int) -> int:
        """
        Delete all messages in a thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Number of messages deleted
        """
        try:
            messages = await self.get_messages_for_thread(thread_id)
            count = len(messages)
            
            for message in messages:
                await self.db.delete(message)
            
            await self.db.commit()
            
            logger.info(
                f"Deleted {count} messages from thread {thread_id}"
            )
            return count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error deleting messages for thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise