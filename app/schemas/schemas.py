# app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# ---- Auth ----
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---- Session ----
class SessionOut(BaseModel):
    id: int
    user_id: int
    agent_type: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# ---- Thread ----
class ThreadCreate(BaseModel):
    title: Optional[str] = None

class ThreadOut(BaseModel):
    id: int
    session_id: int
    title: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# ---- Message ----
class MessageCreate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    response: str
    history: List[MessageOut]
