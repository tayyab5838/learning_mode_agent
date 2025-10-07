from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional, List

# ---- Auth ----
class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")


class UserOut(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload"""
    username: Optional[str] = None
    user_id: Optional[int] = None


# ---- Session ----
class SessionCreate(BaseModel):
    """Schema for creating a new session"""
    agent_type: Optional[str] = Field(None, description="Type of agent for this session")


class SessionOut(BaseModel):
    """Schema for session response"""
    id: int
    user_id: int
    agent_type: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ---- Thread ----
class ThreadCreate(BaseModel):
    """Schema for creating a new thread"""
    title: Optional[str] = Field(None, max_length=200, description="Thread title")


class ThreadOut(BaseModel):
    """Schema for thread response"""
    id: int
    session_id: int
    title: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ThreadWithMessages(ThreadOut):
    """Schema for thread with its messages"""
    messages: List["MessageOut"] = []
    
    model_config = ConfigDict(from_attributes=True)


# ---- Message ----
class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class MessageOut(BaseModel):
    """Schema for message response"""
    id: int
    thread_id: int
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    """Schema for chat request"""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    thread_id: Optional[int] = Field(None, description="Optional thread ID to continue conversation")


class ChatResponse(BaseModel):
    """Schema for chat response"""
    response: str = Field(..., description="AI response")
    history: List[MessageOut] = Field(default_factory=list, description="Conversation history")


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunk"""
    content: str
    is_final: bool = False