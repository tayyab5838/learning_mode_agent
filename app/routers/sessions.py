from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.schemas import SessionOut
from app.utils.db import get_db_session
from app.utils.security import get_current_user
from app.services.session_service import SessionService
from app.models.models import User

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=SessionOut)
async def create_session(agent_type: str | None = None, db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    svc = SessionService(db)
    session = await svc.create_session(current_user.id, agent_type=agent_type)
    return session

@router.get("/", response_model=List[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    svc = SessionService(db)
    sessions = await svc.list_sessions_for_user(current_user.id)
    return sessions
