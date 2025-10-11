from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from app.schemas.schemas import MessageCreate, MessageOut, ChatResponse
from app.utils.db import get_db_session
from app.routers.auth import get_current_user
from app.services.thread_service import ThreadService, ThreadNotFoundError
from app.services.message_service import MessageService
from app.models.models import User

from agents import Runner
from app.agent_services.main_agent import triage_agent, thread_title_generator_Agent
from app.agent_services.agent_config import run_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])


# Add this function in app/routers/messages.py after imports

async def generate_thread_name(first_message: str) -> str:
    """
    Generate a short thread name based on the first message using LLM.
    
    Args:
        first_message: The first user message in the thread
        
    Returns:
        A short, descriptive thread name (max 50 characters)
    """
    try:
        # Create a simple prompt for name generation
        name_prompt = f"Generate a short title for this conversation:\n\n{first_message}"
        
        result = await Runner.run(thread_title_generator_Agent, name_prompt, run_config=run_config)
        thread_name = str(result.final_output).strip()
        
        # Clean up the name
        thread_name = thread_name.replace('"', '').replace("'", '')
        
        # Limit to 50 characters
        if len(thread_name) > 50:
            thread_name = thread_name[:30] + "..."
        
        logger.info(f"Generated thread name: '{thread_name}'")
        return thread_name
        
    except Exception as e:
        logger.error(f"Error generating thread name: {str(e)}", exc_info=True)
        # Fallback to a default name based on first few words
        words = first_message.split()[:5]
        fallback_name = " ".join(words)
        if len(fallback_name) > 50:
            fallback_name = fallback_name[:47] + "..."
        return fallback_name or "New Conversation"


@router.post(
    "/{thread_id}",
    response_model=ChatResponse,
    summary="Send a message",
    description="Send a message to a thread and get AI response",
    responses={
        200: {"description": "Message sent and AI responded"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not allowed to access this thread"},
        404: {"description": "Thread not found"},
        500: {"description": "LLM or server error"}
    }
)
async def send_message(
    thread_id: int = Path(..., description="ID of the thread"),
    payload: MessageCreate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to a thread and get AI response.
    
    **Flow:**
    1. Validates thread exists and belongs to user
    2. Saves user message to database
    3. Sends conversation history to AI
    4. Saves AI response to database
    5. Returns AI response with full conversation history
    
    **Parameters:**
    - **thread_id**: ID of the thread
    - **content**: Message content
    
    **Returns:**
    - AI response and full conversation history
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/messages/1" \\
         -H "Authorization: Bearer <token>" \\
         -H "Content-Type: application/json" \\
         -d '{"content": "Hello, AI!"}'
    ```
    """
    thread_svc = ThreadService(db)
    
    # 1. Verify thread exists
    try:
        thread = await thread_svc.get_thread_by_id(thread_id, load_session=True)
    except ThreadNotFoundError:
        logger.warning(f"Thread {thread_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the thread"
        )
    
    # 2. Verify ownership
    if thread.session.user_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to access thread {thread_id} "
            f"owned by user {thread.session.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to post to this thread"
        )

    msg_svc = MessageService(db)
    
    # 3. Save user message
    try:
        logger.info(
            f"Saving user message to thread {thread_id}: '{payload.content[:50]}...'"
        )
        user_msg = await msg_svc.add_message(  # noqa: F841
            thread_id=thread.id,
            role="user",
            content=payload.content
        )
    except Exception as e:
        logger.error(f"Error saving user message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save message"
        )

    # 4. Fetch conversation history
    try:
        history = await msg_svc.get_messages_for_thread(thread.id)
        messages_for_llm = [
            {"role": m.role, "content": m.content} 
            for m in history
        ]
        logger.info(
            f"Sending {len(messages_for_llm)} messages to LLM for thread {thread_id}"
        )
    except Exception as e:
        logger.error(f"Error fetching message history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message history"
        )

    
    # 4.5. Generate thread name if this is the first message
    is_first_message = len(history) == 1
    if is_first_message and not thread.title:
        try:
            logger.info(f"Generating thread name for thread {thread_id}") 
            thread_name = await generate_thread_name(payload.content)
            # Update thread title
            thread_svc = ThreadService(db)
            await thread_svc.update_thread_title(thread_id, thread_name)
            logger.info(f"Thread {thread_id} named: '{thread_name}'")
        except Exception as e:
            # Don't fail the message if naming fail
            logger.warning(f"Failed to generate thread name for thread {thread_id}: {str(e)}")


    # 5. Run LLM
    try:
        logger.info(f"Running LLM for thread {thread_id}")
        result = await Runner.run(
            triage_agent, 
            messages_for_llm, 
            run_config=run_config
        )
        assistant_reply = str(result.final_output)
        logger.info(
            f"LLM response received for thread {thread_id}: '{assistant_reply[:50]}...'"
        )
    except Exception as e:
        logger.error(
            f"LLM run failed for thread {thread_id}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM run failed: {str(e)}"
        )

    # 6. Save assistant reply
    try:
        assistant_msg = await msg_svc.add_message(  # noqa: F841
            thread_id=thread.id,
            role="assistant",
            content=assistant_reply
        )
        logger.info(f"Assistant message saved to thread {thread_id}")
    except Exception as e:
        logger.error(
            f"Error saving assistant message: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save AI response"
        )

    # 7. Return response with updated history
    try:
        history = await msg_svc.get_messages_for_thread(thread.id)
        return ChatResponse(
            response=assistant_reply,
            thread_id=thread.id,
            history=[MessageOut.model_validate(m) for m in history]
        )
    except Exception as e:
        logger.error(
            f"Error formatting response: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to format response"
        )

@router.get(
    "/{thread_id}",
    response_model=List[MessageOut],
    summary="Get thread history",
    description="Get all messages in a thread",
    responses={
        200: {"description": "List of messages (may be empty)"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not allowed to access this thread"},
        404: {"description": "Thread not found"}
    }
)
async def get_thread_history(
    thread_id: int = Path(..., description="ID of the thread"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all messages in a thread.
    
    **Parameters:**
    - **thread_id**: ID of the thread
    
    **Returns:**
    - List of messages ordered by creation time
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/messages/1" \\
         -H "Authorization: Bearer <token>"
    ```
    """
    thread_svc = ThreadService(db)
    
    # 1. Verify thread exists
    try:
        thread = await thread_svc.get_thread_by_id(thread_id, load_session=True)  # noqa: F841
    except ThreadNotFoundError:
        logger.warning(f"Thread {thread_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the thread"
        )
    msg_svc = MessageService(db)
    msgs = await msg_svc.get_messages_for_thread(thread_id)
    return [MessageOut.from_orm(m) for m in msgs]