from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
import logging

from app.models.models import Thread

logger = logging.getLogger(__name__)


# Custom Exceptions
class ThreadNotFoundError(Exception):
    """Raised when thread is not found"""
    pass


class ThreadCreationError(Exception):
    """Raised when thread creation fails"""
    pass


class ThreadAccessDeniedError(Exception):
    """Raised when user tries to access thread they don't own"""
    pass


class ThreadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_thread(
        self, 
        session_id: int, 
        title: str | None = None
    ) -> Thread:
        """
        Create a new thread for a session.
        
        Args:
            session_id: ID of the session
            title: Optional title for the thread
            
        Returns:
            Created thread
            
        Raises:
            ThreadCreationError: If thread creation fails
        """
        try:
            thread = Thread(session_id=session_id, title=title)
            self.db.add(thread)
            await self.db.commit()
            await self.db.refresh(thread)
            
            logger.info(
                f"Thread created: ID={thread.id}, Session={session_id}, Title='{title}'"
            )
            return thread
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating thread: {str(e)}")
            raise ThreadCreationError(
                "Failed to create thread due to database constraint. "
                "Session may not exist."
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Unexpected error creating thread: {str(e)}", 
                exc_info=True
            )
            raise ThreadCreationError("Failed to create thread")

    async def get_thread_by_id(
        self, 
        thread_id: int, 
        load_session: bool = False
    ) -> Thread:
        """
        Get a thread by its ID.
        
        Args:
            thread_id: ID of the thread
            load_session: Whether to eagerly load the session relationship
            
        Returns:
            Thread object
            
        Raises:
            ThreadNotFoundError: If thread doesn't exist
        """
        try:
            stmt = select(Thread).where(Thread.id == thread_id)
            
            if load_session:
                stmt = stmt.options(selectinload(Thread.session))
            
            result = await self.db.execute(stmt)
            thread = result.scalar_one_or_none()
            
            if not thread:
                logger.warning(f"Thread not found: ID={thread_id}")
                raise ThreadNotFoundError(f"Thread with ID {thread_id} not found")
            
            return thread
            
        except ThreadNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def list_threads_for_session(self, session_id: int) -> list[Thread]:
        """
        Get all threads for a given session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            List of threads (may be empty)
        """
        try:
            stmt = (
                select(Thread)
                .where(Thread.session_id == session_id)
                .order_by(Thread.created_at.desc())  # Most recent first
            )
            result = await self.db.execute(stmt)
            threads = result.scalars().all()
            
            logger.info(
                f"Retrieved {len(threads)} threads for session {session_id}"
            )
            return list(threads)
            
        except Exception as e:
            logger.error(
                f"Error listing threads for session {session_id}: {str(e)}", 
                exc_info=True
            )
            raise

    async def update_thread_title(
        self, 
        thread_id: int, 
        title: str | None
    ) -> Thread:
        """
        Update the title of a thread.
        
        Args:
            thread_id: ID of the thread
            title: New title
            
        Returns:
            Updated thread
            
        Raises:
            ThreadNotFoundError: If thread doesn't exist
        """
        try:
            thread = await self.get_thread_by_id(thread_id)
            
            thread.title = title
            await self.db.commit()
            await self.db.refresh(thread)
            
            logger.info(f"Thread updated: ID={thread_id}, Title='{title}'")
            return thread
            
        except ThreadNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error updating thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise

    
    async def delete_thread(self, thread_id: int) -> None:
        """
        Delete a thread and all its messages.
        
        Args:
            thread_id: ID of the thread to delete
            
        Raises:
            ThreadNotFoundError: If thread doesn't exist
        """
        try:
            thread = await self.get_thread_by_id(thread_id)
            
            await self.db.delete(thread)
            await self.db.commit()
            
            logger.info(f"Thread deleted: ID={thread_id}")
            
        except ThreadNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error deleting thread {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise


    async def verify_thread_ownership(
        self, 
        thread_id: int, 
        user_id: int
    ) -> Thread:
        """
        Verify that a thread belongs to a specific user.
        
        Args:
            thread_id: ID of the thread
            user_id: ID of the user
            
        Returns:
            Thread object if ownership verified
            
        Raises:
            ThreadNotFoundError: If thread doesn't exist
            ThreadAccessDeniedError: If thread doesn't belong to user
        """
        try:
            thread = await self.get_thread_by_id(thread_id, load_session=True)
            
            if thread.session.user_id != user_id:
                logger.warning(
                    f"Access denied: User {user_id} tried to access thread {thread_id} "
                    f"owned by user {thread.session.user_id}"
                )
                raise ThreadAccessDeniedError(
                    "You don't have permission to access this thread"
                )
            
            return thread
            
        except (ThreadNotFoundError, ThreadAccessDeniedError):
            raise
        except Exception as e:
            logger.error(
                f"Error verifying thread ownership {thread_id}: {str(e)}", 
                exc_info=True
            )
            raise