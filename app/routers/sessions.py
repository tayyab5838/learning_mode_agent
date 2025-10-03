# app/routers/sessions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas.schemas import SessionOut
from app.utils.db import get_db
from app.utils.security import get_current_user
from app.services.session_service import SessionService
from app.models.models import User

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=SessionOut)
def create_session(agent_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = SessionService(db)
    session = svc.create_session(current_user.id, agent_type=agent_type)
    return session

@router.get("/", response_model=List[SessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = SessionService(db)
    return svc.list_sessions_for_user(current_user.id)
