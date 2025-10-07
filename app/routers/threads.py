from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.schemas import ThreadCreate, ThreadOut
from app.utils.db import get_db_session
from app.utils.security import get_current_user
from app.services.thread_service import ThreadService
from app.services.session_service import SessionService, SessionNotFoundError
from app.models.models import User

router = APIRouter(prefix="/threads", tags=["threads"])

@router.post("/{session_id}", response_model=ThreadOut)
async def create_thread(session_id: int, payload: ThreadCreate, db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    session_svc = SessionService(db)
    session = await session_svc.get_session_by_id(session_id)
    if not session or session.user_id != current_user.id:
        raise SessionNotFoundError("Session not found")
    t_svc = ThreadService(db)
    thread = await t_svc.create_thread(session_id=session_id, title=payload.title)
    return thread

@router.get("/{session_id}", response_model=List[ThreadOut])
async def list_threads(session_id: int, db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    session_svc = SessionService(db)
    session = await session_svc.get_session_by_id(session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    t_svc = ThreadService(db)
    threads = await t_svc.list_threads_for_session(session_id)
    return threads