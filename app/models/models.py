from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, func, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.utils.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # hashed
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', verified={self.is_verified})>"

class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String, nullable=True)  # optional
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
    threads = relationship("Thread", back_populates="session", cascade="all, delete-orphan")


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("UserSession", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)   # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("Thread", back_populates="messages")


class EmailVerificationToken(Base):
    """Model for email verification tokens"""
    
    __tablename__ = "email_verification_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = relationship("User", back_populates="verification_tokens")
    
    def __repr__(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, used={self.used_at is not None})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_used(self) -> bool:
        """Check if token is used"""
        return self.used_at is not None