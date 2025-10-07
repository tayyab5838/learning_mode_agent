from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import logging

from app.models.models import UserSession

logger = logging.getLogger(__name__)


# Custom Exceptions
class SessionNotFoundError(Exception):
    """Raised when session is not found"""
    pass


class SessionAccessDeniedError(Exception):
    """Raised when user tries to access session they don't own"""
    pass


class SessionCreationError(Exception):
    """Raised when session creation fails"""
    pass

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: int, agent_type: str | None = None) -> UserSession:
        """
        Create a new session for a user.
        
        Args:
            user_id: ID of the user creating the session
            agent_type: Optional agent type for the session
            
        Returns:
            Created session
            
        Raises:
            SessionCreationError: If session creation fails
        """
        try:
            session = UserSession(user_id=user_id, agent_type=agent_type)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            logger.info(f"Session created: ID={session.id}, User={user_id}, Agent={agent_type}")
            return session
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating session: {str(e)}")
            raise SessionCreationError("Failed to create session due to database constraint")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error creating session: {str(e)}", exc_info=True)
            raise SessionCreationError("Failed to create session")


    async def get_session_by_id(self, session_id: int, user_id: int | None = None) -> UserSession:
        """
        Retrieve a session by its ID.
        
        Args:
            session_id: ID of the session
            user_id: Optional user ID to verify ownership
            
        Returns:
            Session object
            
        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionAccessDeniedError: If user doesn't own the session
        """
        try:
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Session not found: ID={session_id}")
                raise SessionNotFoundError(f"Session with ID {session_id} not found")
            
            # Verify ownership if user_id provided
            if user_id is not None and session.user_id != user_id:
                logger.warning(
                    f"Access denied: User {user_id} tried to access session {session_id} "
                    f"owned by user {session.user_id}"
                )
                raise SessionAccessDeniedError("You don't have permission to access this session")

            return session
            
        except (SessionNotFoundError, SessionAccessDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}", exc_info=True)
            raise
            
    async def list_sessions_for_user(self, user_id: int) -> list[UserSession]:
        """
        Retrieve all sessions belonging to a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of sessions (may be empty)
        """
        try:
            stmt = (
                select(UserSession)
                .where(UserSession.user_id == user_id)
                .order_by(UserSession.created_at.desc())  # Most recent first
            )
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()
            
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return list(sessions)
            
        except Exception as e:
            logger.error(f"Error listing sessions for user {user_id}: {str(e)}", exc_info=True)
            raise

    async def delete_session(self, session_id: int, user_id: int) -> None:
        """
        Delete a session.
        
        Args:
            session_id: ID of the session to delete
            user_id: ID of the user (for ownership verification)
            
        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionAccessDeniedError: If user doesn't own the session
        """
        try:
            # Get session and verify ownership
            session = await self.get_session_by_id(session_id, user_id)
            
            await self.db.delete(session)
            await self.db.commit()
            
            logger.info(f"Session deleted: ID={session_id}, User={user_id}")
            
        except (SessionNotFoundError, SessionAccessDeniedError):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting session {session_id}: {str(e)}", exc_info=True)
            raise


    async def update_session_agent_type(
        self, 
        session_id: int, 
        user_id: int, 
        agent_type: str | None
    ) -> UserSession:
        """
        Update the agent type of a session.
        
        Args:
            session_id: ID of the session
            user_id: ID of the user (for ownership verification)
            agent_type: New agent type
            
        Returns:
            Updated session
            
        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionAccessDeniedError: If user doesn't own the session
        """
        try:
            # Get session and verify ownership
            session = await self.get_session_by_id(session_id, user_id)
            
            session.agent_type = agent_type
            await self.db.commit()
            await self.db.refresh(session)
            
            logger.info(f"Session updated: ID={session_id}, Agent={agent_type}")
            return session
            
        except (SessionNotFoundError, SessionAccessDeniedError):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating session {session_id}: {str(e)}", exc_info=True)
            raise