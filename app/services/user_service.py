from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.models import User
from app.schemas.schemas import UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token


class UserAlreadyExistsError(Exception):
    """Raised when user already exists"""
    pass


class UserNotFoundError(Exception):
    """Raised when user is not found"""
    pass


class InvalidCredentialsError(Exception):
    """Raised when credentials are invalid"""
    pass

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, payload: UserCreate) -> User:
        """
        Register a new user.

        Args:
            payload (UserCreate): {
                username: str,
                email: EmailStr,
                password: str
            }

        Raises:
            HTTPException: If username or email already exists.

        Returns:
            User: Newly created user.
        """        
        stmt = select(User).where(or_(User.username == payload.username, User.email == payload.email))
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise UserAlreadyExistsError(f"Username '{payload.username}' already exists")
        result = await self.db.execute(
            select(User).where(User.email == payload.email)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsError(f"Email '{payload.email}' already exists")
     
        hashed = get_password_hash(payload.password)
        new_user = User(username=payload.username, email=payload.email, password=hashed)
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def authenticate_user(self, username: str, password: str):
        """
        Authenticate user with username and password.
        """
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        print("user :", user)
        if not user or not verify_password(password, user.password):
            raise InvalidCredentialsError("Invalid credentials")
        return user

    async def create_token_for_user(self, user) -> str:
        """
        Create JWT token for the user.
        """
        token = create_access_token(data={"sub": str(user.id)})
        return token

    async def get_by_username(self, username: str):
        """
        Retrieve a user by username.
        """
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User:
        """
        Get user by email.
        
        Raises:
            UserNotFoundError: If user not found
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(f"User with email '{email}' not found")
        
        return user

    async def create_token_for_user(self, user: User) -> str:  # noqa: F811
        """Create JWT token for user"""
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "email": user.email
        }
        return create_access_token(token_data)