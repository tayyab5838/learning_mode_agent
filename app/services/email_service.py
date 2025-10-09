import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
import secrets
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, EmailVerificationToken
from app.config import settings

logger = logging.getLogger(__name__)


# Custom Exceptions
class EmailSendError(Exception):
    """Raised when email sending fails"""
    pass


class VerificationTokenError(Exception):
    """Raised when verification token is invalid or expired"""
    pass


class EmailService:
    """Service for handling email-related operations"""
    
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
            
            logger.info(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            raise EmailSendError(f"Failed to send email: {str(e)}")
    
    async def generate_verification_token(self, user_id: int) -> str:
        """
        Generate and store email verification token.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Verification token string
        """
        try:
            # Generate secure random token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
            )
            
            # Store token in database
            verification_token = EmailVerificationToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at
            )
            
            self.db.add(verification_token)
            await self.db.commit()
            
            logger.info(f"Verification token generated for user {user_id}")
            return token
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to generate verification token for user {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    async def send_verification_email(self, user: User, token: str):
        """
        Send verification email to user.
        
        Args:
            user: User object
            token: Verification token
            
        Raises:
            EmailSendError: If email sending fails
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # HTML version
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 30px; 
                    background-color: #4CAF50; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Learning Mode Agent!</h1>
                </div>
                <div class="content">
                    <h2>Hi {user.username},</h2>
                    <p>Thank you for registering! Please verify your email address to complete your registration.</p>
                    <p>Click the button below to verify your email:</p>
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </div>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{verification_url}</p>
                    <p><strong>This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</strong></p>
                    <p>If you didn't create an account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Learning Mode Agent. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Welcome to Learning Mode Agent!
        
        Hi {user.username},
        
        Thank you for registering! Please verify your email address to complete your registration.
        
        Click this link to verify your email:
        {verification_url}
        
        This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.
        
        If you didn't create an account, please ignore this email.
        
        © 2024 Learning Mode Agent. All rights reserved.
        """
        
        subject = "Verify Your Email Address - Learning Mode Agent"
        
        self._send_email(user.email, subject, html_content, text_content)
        logger.info(f"Verification email sent to {user.email}")
    
    async def verify_email_token(self, token: str) -> User:
        """
        Verify email token and mark user as verified.
        
        Args:
            token: Verification token
            
        Returns:
            Verified user
            
        Raises:
            VerificationTokenError: If token is invalid or expired
        """
        try:
            # Find token in database
            stmt = select(EmailVerificationToken).where(
                EmailVerificationToken.token == token
            )
            result = await self.db.execute(stmt)
            verification_token = result.scalar_one_or_none()
            
            if not verification_token:
                raise VerificationTokenError("Invalid verification token")
            
            # Check if token is expired
            if verification_token.expires_at < datetime.now(timezone.utc):
                raise VerificationTokenError("Verification token has expired")
            
            # Check if already used
            if verification_token.used_at:
                raise VerificationTokenError("Verification token has already been used")
            
            # Get user
            user_stmt = select(User).where(User.id == verification_token.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise VerificationTokenError("User not found")
            
            # Mark user as verified
            user.is_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            
            # Mark token as used
            verification_token.used_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Email verified for user {user.id} ({user.email})")
            return user
            
        except VerificationTokenError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error verifying email token: {str(e)}", exc_info=True)
            raise VerificationTokenError(f"Verification failed: {str(e)}")
    
    async def resend_verification_email(self, user: User):
        """
        Resend verification email to user.
        
        Args:
            user: User object
            
        Raises:
            ValueError: If user is already verified
            EmailSendError: If email sending fails
        """
        if user.is_verified:
            raise ValueError("User email is already verified")
        
        # Generate new token
        token = await self.generate_verification_token(user.id)
        
        # Send email
        await self.send_verification_email(user, token)
        
        logger.info(f"Verification email resent to {user.email}")
    
    async def delete_expired_tokens(self):
        """Delete expired verification tokens (cleanup task)"""
        try:
            stmt = select(EmailVerificationToken).where(
                EmailVerificationToken.expires_at < datetime.now(timezone.utc)
            )
            result = await self.db.execute(stmt)
            expired_tokens = result.scalars().all()
            
            for token in expired_tokens:
                await self.db.delete(token)
            
            await self.db.commit()
            
            logger.info(f"Deleted {len(expired_tokens)} expired verification tokens")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting expired tokens: {str(e)}", exc_info=True)