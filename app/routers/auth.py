# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import UserCreate, UserOut, Token
from app.utils.db import get_db
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    svc = UserService(db)
    user = svc.register_user(user_data)
    return user

@router.post("/login", response_model=Token)
def login(username: str, password: str, db: Session = Depends(get_db)):
    svc = UserService(db)
    user = svc.authenticate_user(username, password)
    token = svc.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}
