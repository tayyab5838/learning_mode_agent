from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.schemas.schemas import UserCreate, UserOut, Token
from app.utils.db import get_db_session
from app.utils.security import get_current_user
from app.services.user_service import (
    UserService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["User"])


# ============================================================================
# ENDPOINT: Register User
# ============================================================================

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password",
    responses={
        201: {
            "description": "User successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "johndoe",
                        "email": "john@example.com",
                        "created_at": "2024-01-01T00:00:00"
                    }
                }
            }
        },
        400: {
            "description": "Bad request - User already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Username 'johndoe' already exists"}
                }
            }
        },
        422: {
            "description": "Validation error - Invalid input format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        },
        500: {"description": "Internal server error"}
    }
)
async def register(
    user_data: UserCreate = Body(
        ...,
        example={
            "username": "johndoe",
            "email": "john@example.com",
            "password": "securepassword123"
        }
    ),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Register a new user account.
    
    **Parameters:**
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address (must be unique)
    - **password**: Secure password (minimum 8 characters)
    
    **Returns:**
    - User information without password
    
    **Errors:**
    - 400: Username or email already exists
    - 422: Invalid input format (validation error)
    - 500: Server error during registration
    """
    svc = UserService(db)
    
    try:
        logger.info(f"Attempting to register user: {user_data.username}")
        user = await svc.register_user(user_data)
        logger.info(f"User registered successfully: {user.username} (ID: {user.id})")
        return user
        
    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration. Please try again later."
        )

@router.post("/login", response_model=Token)
async def login(username: str, password: str, db: AsyncSession = Depends(get_db_session)):
    """
    Login with username and password (OAuth2 compatible).
    
    **Form Parameters:**
    - **username**: User's username
    - **password**: User's password
    
    **Returns:**
    - JWT access token for authenticated requests
    - Token type (always "bearer")
    
    **Usage:**
    ```bash
    curl -X POST "http://localhost:8000/auth/login" \\
         -H "Content-Type: application/x-www-form-urlencoded" \\
         -d "username=johndoe&password=secret"
    ```
    
    **Errors:**
    - 401: Invalid username or password
    - 422: Missing required fields
    - 500: Server error during authentication
    """
    svc = UserService(db)
    
    try:
        logger.info(f"Login attempt for user: {username}")
        
        # Authenticate user
        user = await svc.authenticate_user(username, password)
        
        # Generate token
        token = await svc.create_token_for_user(user)
        
        logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")
        
        return {
            "access_token": token,
            "token_type": "bearer"
        }
        
    except InvalidCredentialsError:
        logger.warning(f"Login failed for user '{username}': Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login. Please try again later."
        )


# ============================================================================
# ENDPOINT: Get Current User (Protected Route Example)
# ============================================================================

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Get the currently authenticated user's information",
)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile.
    
    **Requires:**
    - Valid JWT token in Authorization header
    
    **Headers:**
    ```
    Authorization: Bearer <your_token_here>
    ```
    
    **Returns:**
    - Current user's profile information
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/auth/me" \\
         -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """
    logger.info(f"User {current_user.username} accessed /me endpoint")
    return current_user




# =============================================================================
# ENDPOINT: Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Health check",
    description="Check if the authentication service is running",
    status_code=status.HTTP_200_OK,
    tags=["Health"]
)
async def health_check():
    """
    Simple health check endpoint.
    
    **Returns:**
    - Service status
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }