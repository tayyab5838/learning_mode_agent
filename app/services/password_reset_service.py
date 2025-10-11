import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
import secrets
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User
from app.models.models import PasswordResetToken
from app.config import settings
from app.utils.security import get_password_hash

logger = logging.getLogger(__name__)


# Custom Exceptions
class PasswordResetError(Exception):
    """Base exception for password reset errors"""
    pass


class InvalidResetTokenError(Exception):
    """Raised when reset token is invalid or expired"""
    pass


class EmailSendError(Exception):
    """Raised when email sending fails"""
    pass


class PasswordResetService:
    """Service for handling password reset functionality"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str, text_content: str):
        """
        Send email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML version of email
            text_content: Plain text version of email
            
        Raises:
            EmailSendError: If email sending fails
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = settings.SMTP_FROM_EMAIL
            message["To"] = to_email
            
            # Attach plain text and HTML versions
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                server.send_message(message)
            
            logger.info(f"Password reset email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            raise EmailSendError(f"Failed to send email: {str(e)}")
    
    async def generate_reset_token(self, user_id: int) -> str:
        """
        Generate and store password reset token.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Reset token string
        """
        try:
            # Invalidate any existing unused tokens for this user
            stmt = select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None)
            )
            result = await self.db.execute(stmt)
            existing_tokens = result.scalars().all()
            
            for token in existing_tokens:
                token.used_at = datetime.now(timezone.utc)
            
            # Generate secure random token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
            )
            
            # Store token in database
            reset_token = PasswordResetToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at
            )
            
            self.db.add(reset_token)
            await self.db.commit()
            
            logger.info(f"Password reset token generated for user {user_id}")
            return token
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to generate reset token for user {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    async def send_password_reset_email(self, user: User, token: str):
        """
        Send password reset email to user.
        
        Args:
            user: User object
            token: Reset token
            
        Raises:
            EmailSendError: If email sending fails
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        # HTML version
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 30px; 
                    background-color: #f44336; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
                .warning {{ 
                    background-color: #fff3cd; 
                    border-left: 4px solid #ffc107; 
                    padding: 15px; 
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.username},</h2>
                    <p>We received a request to reset your password. If you made this request, click the button below to reset your password:</p>
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </div>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_url}</p>
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hours</li>
                            <li>This link can only be used once</li>
                            <li>If you didn't request this, please ignore this email</li>
                            <li>Your password will not change unless you click the link and set a new password</li>
                        </ul>
                    </div>
                    <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Learning Mode Agent. All rights reserved.</p>
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Password Reset Request
        
        Hi {user.username},
        
        We received a request to reset your password. If you made this request, click the link below to reset your password:
        
        {reset_url}
        
        SECURITY NOTICE:
        - This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hours
        - This link can only be used once
        - If you didn't request this, please ignore this email
        - Your password will not change unless you click the link and set a new password
        
        If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
        
        © 2024 Learning Mode Agent. All rights reserved.
        This is an automated message, please do not reply to this email.
        """
        
        subject = "Reset Your Password - Learning Mode Agent"
        
        self._send_email(user.email, subject, html_content, text_content)
        logger.info(f"Password reset email sent to {user.email}")
    
    async def verify_reset_token(self, token: str) -> PasswordResetToken:
        """
        Verify password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            PasswordResetToken object
            
        Raises:
            InvalidResetTokenError: If token is invalid, expired, or used
        """
        try:
            # Find token in database
            stmt = select(PasswordResetToken).where(
                PasswordResetToken.token == token
            )
            result = await self.db.execute(stmt)
            reset_token = result.scalar_one_or_none()
            
            if not reset_token:
                raise InvalidResetTokenError("Invalid reset token")
            
            # Check if token is expired
            if reset_token.expires_at < datetime.now(timezone.utc):
                raise InvalidResetTokenError("Reset token has expired")
            
            # Check if already used
            if reset_token.used_at:
                raise InvalidResetTokenError("Reset token has already been used")
            
            return reset_token
            
        except InvalidResetTokenError:
            raise
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}", exc_info=True)
            raise InvalidResetTokenError(f"Token verification failed: {str(e)}")
    
    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user password using token.
        
        Args:
            token: Reset token
            new_password: New password (plain text)
            
        Returns:
            Updated user
            
        Raises:
            InvalidResetTokenError: If token is invalid
        """
        try:
            # Verify token
            reset_token = await self.verify_reset_token(token)
            
            # Get user
            user_stmt = select(User).where(User.id == reset_token.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise InvalidResetTokenError("User not found")
            
            # Update password
            user.password = get_password_hash(new_password)
            
            # Mark token as used
            reset_token.used_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Password reset successfully for user {user.id}")
            return user
            
        except InvalidResetTokenError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            raise PasswordResetError(f"Password reset failed: {str(e)}")
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset for a user by email.
        
        Args:
            email: User's email address
            
        Returns:
            True if email was sent (or user doesn't exist but we don't reveal that)
            
        Note:
            This method doesn't reveal whether the email exists for security reasons
        """
        try:
            # Find user by email
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                # Don't reveal that user doesn't exist
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True
            
            # Generate token
            token = await self.generate_reset_token(user.id)
            
            # Send email
            await self.send_password_reset_email(user, token)
            
            logger.info(f"Password reset email sent to {email}")
            return True
            
        except EmailSendError as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in password reset request: {str(e)}", exc_info=True)
            raise
    
    async def delete_expired_tokens(self):
        """Delete expired reset tokens (cleanup task)"""
        try:
            stmt = select(PasswordResetToken).where(
                PasswordResetToken.expires_at < datetime.now(timezone.utc)
            )
            result = await self.db.execute(stmt)
            expired_tokens = result.scalars().all()
            
            for token in expired_tokens:
                await self.db.delete(token)
            
            await self.db.commit()
            
            logger.info(f"Deleted {len(expired_tokens)} expired password reset tokens")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting expired tokens: {str(e)}", exc_info=True)