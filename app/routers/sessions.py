from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from app.schemas.schemas import SessionOut
from app.utils.db import get_db_session
from app.routers.auth import get_current_user
from app.services.session_service import (
    SessionService,
    SessionNotFoundError,
    SessionAccessDeniedError,
    SessionCreationError
)
from app.models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "/",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new session for the authenticated user"
)
async def create_session(
    agent_type: str | None = Query(None, description="Type of agent for this session"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new session for the authenticated user.
    
    **Parameters:**
    - **agent_type**: Optional agent type (e.g., "learning_mode", "assistant_mode")
    
    **Returns:**
    - Created session with ID and metadata
    """
    svc = SessionService(db)
    
    try:
        logger.info(f"Creating session for user {current_user.id} with agent_type={agent_type}")
        session = await svc.create_session(current_user.id, agent_type=agent_type)
        logger.info(f"Session created successfully: ID={session.id}, User={current_user.id}")
        return session
        
    except SessionCreationError as e:
        logger.error(f"Session creation failed for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error creating session for user {current_user.id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the session"
        )


@router.get(
    "/",
    response_model=List[SessionOut],
    summary="List user sessions",
    description="Get all sessions for the authenticated user"
)
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all sessions for the authenticated user.
    
    **Returns:**
    - List of sessions ordered by most recent first
    """
    svc = SessionService(db)
    
    try:
        logger.info(f"Listing sessions for user {current_user.id}")
        sessions = await svc.list_sessions_for_user(current_user.id)
        logger.info(f"Retrieved {len(sessions)} sessions for user {current_user.id}")
        return sessions
        
    except Exception as e:
        logger.error(
            f"Error listing sessions for user {current_user.id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving sessions"
        )


@router.get(
    "/{session_id}",
    response_model=SessionOut,
    summary="Get session by ID",
    description="Get a specific session by ID (must be owned by authenticated user)"
)
async def get_session(
    session_id: int = Path(..., description="Session ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific session by ID.
    
    **Parameters:**
    - **session_id**: ID of the session
    
    **Returns:**
    - Session details
    """
    svc = SessionService(db)
    
    try:
        logger.info(f"User {current_user.id} requesting session {session_id}")
        session = await svc.get_session_by_id(session_id, user_id=current_user.id)
        return session
        
    except SessionNotFoundError as e:
        logger.warning(f"Session {session_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except SessionAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied access to session {session_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving session {session_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete session",
    description="Delete a specific session (must be owned by authenticated user)"
)
async def delete_session(
    session_id: int = Path(..., description="Session ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a session.
    
    **Parameters:**
    - **session_id**: ID of the session to delete
    
    **Returns:**
    - 204 No Content on success
    """
    svc = SessionService(db)
    
    try:
        logger.info(f"User {current_user.id} deleting session {session_id}")
        await svc.delete_session(session_id, user_id=current_user.id)
        logger.info(f"Session {session_id} deleted by user {current_user.id}")
        
    except SessionNotFoundError as e:
        logger.warning(f"Session {session_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except SessionAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied deletion of session {session_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error deleting session {session_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.patch(
    "/{session_id}",
    response_model=SessionOut,
    summary="Update session",
    description="Update session agent type"
)
async def update_session(
    session_id: int = Path(..., description="Session ID"),
    agent_type: str | None = Body(..., embed=True, description="New agent type"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a session's agent type.
    
    **Parameters:**
    - **session_id**: ID of the session
    - **agent_type**: New agent type value
    
    **Returns:**
    - Updated session
    """
    svc = SessionService(db)
    
    try:
        logger.info(
            f"User {current_user.id} updating session {session_id} "
            f"with agent_type={agent_type}"
        )
        session = await svc.update_session_agent_type(
            session_id, 
            user_id=current_user.id, 
            agent_type=agent_type
        )
        logger.info(f"Session {session_id} updated successfully")
        return session
        
    except SessionNotFoundError as e:
        logger.warning(f"Session {session_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except SessionAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied update of session {session_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error updating session {session_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )