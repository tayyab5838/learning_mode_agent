from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import MessageCreate, MessageOut, ChatResponse
from app.utils.db import get_db
from app.utils.security import get_current_user
from app.services.thread_service import ThreadService
from app.services.message_service import MessageService
from app.models.models import User

from agents import Runner
from app.agent_services.main_agent import triage_agent
from app.agent_services.agent_config import run_config

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("/{thread_id}", response_model=ChatResponse)
async def send_message(thread_id: int, payload: MessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    thread_svc = ThreadService(db)
    thread = thread_svc.get_thread_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    # ensure thread belongs to the current user's session
    if thread.session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to post to this thread")

    msg_svc = MessageService(db)
    # 1. save user message
    user_msg = msg_svc.add_message(thread_id=thread.id, role="user", content=payload.content)  # noqa: F841

    # 2. fetch history
    history = msg_svc.get_messages_for_thread(thread.id)
    # prepare messages in the format your Runner/agent expects:
    messages_for_llm = [{"role": m.role, "content": m.content} for m in history]

    # 3. run LLM
    try:
        result = await Runner.run(triage_agent, messages_for_llm, run_config=run_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM run failed: {e}")

    # 4. save assistant reply
    assistant_reply = str(result.final_output)
    assistant_msg = msg_svc.add_message(thread_id=thread.id, role="assistant", content=assistant_reply)  # noqa: F841

    # 5. return combined history (or just the response + history)
    history = msg_svc.get_messages_for_thread(thread.id)
    return ChatResponse(response=assistant_reply, history=[MessageOut.from_orm(m) for m in history])

@router.get("/{thread_id}", response_model=List[MessageOut])
def get_thread_history(thread_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    thread_svc = ThreadService(db)
    thread = thread_svc.get_thread_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    msg_svc = MessageService(db)
    msgs = msg_svc.get_messages_for_thread(thread_id)
    return [MessageOut.from_orm(m) for m in msgs]
