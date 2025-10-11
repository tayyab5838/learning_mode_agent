from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.utils.db import get_db_session
from app.utils.security import get_current_user
from app.schemas.schemas import (
    UserCreate, UserOut, Token,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetResponse
)
from app.services.user_service import (
    UserService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError
)
from app.services.email_service import (
    EmailService,
    EmailSendError,
    VerificationTokenError
)

from app.services.password_reset_service import (
    PasswordResetService,
    InvalidResetTokenError,
    PasswordResetError
)

from app.config import settings

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

         # Send verification email (don't fail registration if email fails)
        if settings.EMAIL_VERIFICATION_REQUIRED:
            try:
                email_svc = EmailService(db)
                token = await email_svc.generate_verification_token(user.id)
                await email_svc.send_verification_email(user, token)
                logger.info(f"Verification email sent to {user.email}")
            except EmailSendError as e:
                logger.warning(f"Failed to send verification email: {str(e)}")
                # Don't fail registration, user can request resend later
        
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


@router.get(
    "/verify-email",
    summary="Verify email address",
    description="Verify user email using token from email",
    responses={
        200: {"description": "Email verified successfully"},
        400: {"description": "Invalid or expired token"}
    }
)
async def verify_email(
    token: str = Query(..., description="Verification token from email"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Verify user email address.
    
    **Parameters:**
    - **token**: Verification token received via email
    
    **Returns:**
    - Success message
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/auth/verify-email?token=<token>"
    ```
    """
    email_svc = EmailService(db)
    
    try:
        logger.info("Email verification attempted with token")
        user = await email_svc.verify_email_token(token)
        logger.info(f"Email verified successfully for user {user.id}")
        
        return {
            "message": "Email verified successfully",
            "username": user.username,
            "email": user.email
        }
        
    except VerificationTokenError as e:
        logger.warning(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification"
        )


# ============================================================================
# ENDPOINT: Resend Verification Email
# ============================================================================

@router.post(
    "/resend-verification",
    summary="Resend verification email",
    description="Resend verification email to user",
    responses={
        200: {"description": "Verification email sent"},
        400: {"description": "User already verified or not found"},
        429: {"description": "Too many requests"}
    }
)
async def resend_verification_email(
    email: str = Body(..., embed=True, description="User email address"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Resend verification email to user.
    
    **Parameters:**
    - **email**: User's email address
    
    **Returns:**
    - Success message
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/auth/resend-verification" \\
         -H "Content-Type: application/json" \\
         -d '{"email": "user@example.com"}'
    ```
    """
    user_svc = UserService(db)
    email_svc = EmailService(db)
    
    try:
        # Find user by email
        user = await user_svc.get_user_by_email(email)
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Resend verification email
        await email_svc.resend_verification_email(user)
        logger.info(f"Verification email resent to {email}")
        
        return {
            "message": "Verification email sent successfully",
            "email": email
        }
        
    except UserNotFoundError:
        # Don't reveal if user exists
        logger.warning(f"Verification resend attempted for non-existent email: {email}")
        return {
            "message": "If the email exists, a verification email has been sent",
            "email": email
        }
        
    except EmailSendError as e:
        logger.error(f"Failed to resend verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )
        
    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resending verification email"
        )


# ============================================================================
# ENDPOINT: Request Password Reset
# ============================================================================

@router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
    summary="Request password reset",
    description="Send password reset email to user",
    responses={
        200: {"description": "Password reset email sent"},
        500: {"description": "Failed to send email"}
    }
)
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Request password reset email.
    
    **Parameters:**
    - **email**: User's email address
    
    **Returns:**
    - Success message (doesn't reveal if email exists)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/auth/forgot-password" \\
         -H "Content-Type: application/json" \\
         -d '{"email": "user@example.com"}'
    ```
    
    **Note:** For security, this endpoint always returns success,
    even if the email doesn't exist in the system.
    """
    reset_svc = PasswordResetService(db)
    
    try:
        logger.info(f"Password reset requested for email: {request.email}")
        await reset_svc.request_password_reset(request.email)
        
        # Always return success to prevent email enumeration
        return PasswordResetResponse(
            message="If that email address is in our system, we have sent you a password reset link.",
            email=request.email
        )
        
    except EmailSendError as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email. Please try again later."
        )
        
    except Exception as e:
        logger.error(f"Error processing password reset request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


# ============================================================================
# ENDPOINT: Reset Password
# ============================================================================

@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    summary="Reset password",
    description="Reset password using token from email",
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired token"},
        422: {"description": "Validation error"}
    }
)
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reset password using token from email.
    
    **Parameters:**
    - **token**: Reset token from email
    - **new_password**: New password (minimum 8 characters)
    
    **Returns:**
    - Success message
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/auth/reset-password" \\
         -H "Content-Type: application/json" \\
         -d '{
           "token": "abc123...",
           "new_password": "newSecurePassword123"
         }'
    ```
    """
    reset_svc = PasswordResetService(db)
    
    try:
        logger.info("Password reset attempted with token")
        user = await reset_svc.reset_password(request.token, request.new_password)
        logger.info(f"Password reset successfully for user {user.id}")
        
        return PasswordResetResponse(
            message="Password has been reset successfully. You can now log in with your new password."
        )
        
    except InvalidResetTokenError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except PasswordResetError as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password. Please try again."
        )
        
    except Exception as e:
        logger.error(f"Error during password reset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting password"
        )


# ============================================================================
# ENDPOINT: Verify Reset Token (Optional)
# ============================================================================

@router.get(
    "/verify-reset-token",
    summary="Verify reset token",
    description="Check if a password reset token is valid",
    responses={
        200: {"description": "Token is valid"},
        400: {"description": "Token is invalid or expired"}
    }
)
async def verify_reset_token(
    token: str = Query(..., description="Reset token to verify"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Verify if a password reset token is valid.
    
    **Parameters:**
    - **token**: Reset token to verify
    
    **Returns:**
    - Token validity status
    
    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/auth/verify-reset-token?token=<token>"
    ```
    
    **Use Case:** Frontend can call this before showing the reset password form
    """
    reset_svc = PasswordResetService(db)
    
    try:
        reset_token = await reset_svc.verify_reset_token(token)
        
        return {
            "valid": True,
            "message": "Token is valid",
            "expires_at": reset_token.expires_at.isoformat()
        }
        
    except InvalidResetTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(f"Error verifying reset token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying token"
        )