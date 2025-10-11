from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.models import User
from app.schemas.schemas import UserCreate, UserOut
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

    async def register_user(self, user_data: UserCreate) -> UserOut:
        """
        Register a new user.
        
        Raises:
            UserAlreadyExistsError: If username or email already exists
        """
        # Check if username exists
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsError(f"Username '{user_data.username}' already exists")
        
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsError(f"Email '{user_data.email}' already exists")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password
        )
        
        self.db.add(new_user)
        
        try:
            await self.db.commit()
            await self.db.refresh(new_user)
        except IntegrityError:
            await self.db.rollback()
            raise UserAlreadyExistsError("User with this username or email already exists")
        
        return new_user

    async def authenticate_user(self, username: str, password: str) -> User:
        """
        Authenticate a user.
        
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        from app.config import settings  # noqa: F401
        
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise InvalidCredentialsError("Incorrect username or password")
        
        if not verify_password(password, user.password):
            raise InvalidCredentialsError("Incorrect username or password")
        
        # Optionally check email verification
        if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_verified:
            raise InvalidCredentialsError(
                "Email not verified. Please check your email for verification link."
            )
        
        return user

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by ID.
        
        Raises:
            UserNotFoundError: If user not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(f"User with id {user_id} not found")
        
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        Get user by username.
        
        Raises:
            UserNotFoundError: If user not found
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        return user

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

    async def create_token_for_user(self, user: User) -> str:
        """Create JWT token for user"""
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "email": user.email
        }
        return create_access_token(data=token_data)