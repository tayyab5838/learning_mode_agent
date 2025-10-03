from sqlalchemy.orm import Session
from app.models.models import User
from app.schemas.schemas import UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token
from fastapi import HTTPException, status

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, payload: UserCreate) -> User:
        # unique username/email check
        existing = self.db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")
        hashed = get_password_hash(payload.password)
        user = User(username=payload.username, email=payload.email, password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str):
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    def create_token_for_user(self, user) -> str:
        token = create_access_token(data={"sub": str(user.id)})
        return token

    def get_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()
