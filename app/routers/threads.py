from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from app.schemas.schemas import ThreadCreate, ThreadOut
from app.utils.db import get_db_session
from app.routers.auth import get_current_user
from app.services.thread_service import (
    ThreadService,
    ThreadNotFoundError,
    ThreadCreationError,
    ThreadAccessDeniedError
)
from app.services.session_service import (
    SessionService,
    SessionNotFoundError,
    SessionAccessDeniedError
)
from app.models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threads", tags=["Threads"])


@router.post(
    "/{session_id}",
    response_model=ThreadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new thread",
    description="Create a new thread within a session"
)
async def create_thread(
    session_id: int = Path(..., description="ID of the session"),
    payload: ThreadCreate = Body(..., example={"title": "My Discussion Thread"}),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new thread in a session.
    
    **Parameters:**
    - **session_id**: ID of the session (must be owned by current user)
    - **title**: Optional title for the thread
    
    **Returns:**
    - Created thread with ID and metadata
    """
    session_svc = SessionService(db)
    thread_svc = ThreadService(db)
    
    try:
        # Verify session exists and belongs to current user
        logger.info(
            f"User {current_user.id} creating thread in session {session_id}"
        )
        session = await session_svc.get_session_by_id(session_id, user_id=current_user.id)  # noqa: F841
        
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
    
    # Create thread
    try:
        thread = await thread_svc.create_thread(
            session_id=session_id, 
            title=payload.title
        )
        logger.info(
            f"Thread created successfully: ID={thread.id}, "
            f"Session={session_id}, User={current_user.id}"
        )
        return thread
        
    except ThreadCreationError as e:
        logger.error(
            f"Failed to create thread in session {session_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error creating thread in session {session_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the thread"
        )


@router.get(
    "/{session_id}",
    response_model=List[ThreadOut],
    summary="List threads in session",
    description="Get all threads in a session"
)
async def list_threads(
    session_id: int = Path(..., description="ID of the session"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all threads in a session.
    
    **Parameters:**
    - **session_id**: ID of the session (must be owned by current user)
    
    **Returns:**
    - List of threads ordered by creation time
    """
    session_svc = SessionService(db)
    thread_svc = ThreadService(db)
    
    try:
        # Verify session exists and belongs to current user
        logger.info(f"User {current_user.id} listing threads in session {session_id}")
        session = await session_svc.get_session_by_id(session_id, user_id=current_user.id)  # noqa: F841
        
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
    
    # List threads
    try:
        threads = await thread_svc.list_threads_for_session(session_id)
        logger.info(
            f"Retrieved {len(threads)} threads for session {session_id}, "
            f"User {current_user.id}"
        )
        return threads
        
    except Exception as e:
        logger.error(
            f"Error listing threads for session {session_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving threads"
        )


@router.get(
    "/thread/{thread_id}",
    response_model=ThreadOut,
    summary="Get thread by ID",
    description="Get a specific thread by ID"
)
async def get_thread(
    thread_id: int = Path(..., description="ID of the thread"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific thread by ID.
    
    **Parameters:**
    - **thread_id**: ID of the thread
    
    **Returns:**
    - Thread details
    """
    thread_svc = ThreadService(db)
    
    try:
        logger.info(f"User {current_user.id} requesting thread {thread_id}")
        thread = await thread_svc.verify_thread_ownership(thread_id, current_user.id)
        return thread
        
    except ThreadNotFoundError as e:
        logger.warning(f"Thread {thread_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except ThreadAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied access to thread {thread_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving thread {thread_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.patch(
    "/thread/{thread_id}",
    response_model=ThreadOut,
    summary="Update thread",
    description="Update thread title"
)
async def update_thread(
    thread_id: int = Path(..., description="ID of the thread"),
    title: str | None = Body(..., embed=True, description="New thread title"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a thread's title.
    
    **Parameters:**
    - **thread_id**: ID of the thread
    - **title**: New title for the thread
    
    **Returns:**
    - Updated thread
    """
    thread_svc = ThreadService(db)
    
    try:
        # Verify ownership
        logger.info(
            f"User {current_user.id} updating thread {thread_id} "
            f"with title='{title}'"
        )
        await thread_svc.verify_thread_ownership(thread_id, current_user.id)
        
        # Update thread
        thread = await thread_svc.update_thread_title(thread_id, title)
        logger.info(f"Thread {thread_id} updated successfully")
        return thread
        
    except ThreadNotFoundError as e:
        logger.warning(f"Thread {thread_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except ThreadAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied update of thread {thread_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error updating thread {thread_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete(
    "/thread/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete thread",
    description="Delete a thread and all its messages"
)
async def delete_thread(
    thread_id: int = Path(..., description="ID of the thread"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a thread and all its messages.
    
    **Parameters:**
    - **thread_id**: ID of the thread to delete
    
    **Returns:**
    - 204 No Content on success
    """
    thread_svc = ThreadService(db)
    
    try:
        # Verify ownership
        logger.info(f"User {current_user.id} deleting thread {thread_id}")
        await thread_svc.verify_thread_ownership(thread_id, current_user.id)
        
        # Delete thread
        await thread_svc.delete_thread(thread_id)
        logger.info(f"Thread {thread_id} deleted by user {current_user.id}")
        
    except ThreadNotFoundError as e:
        logger.warning(f"Thread {thread_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
        
    except ThreadAccessDeniedError as e:
        logger.warning(
            f"User {current_user.id} denied deletion of thread {thread_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(
            f"Error deleting thread {thread_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )