import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Determine which environment to load
env = os.getenv("ENV", "development")

# Load appropriate .env file
if env == "test":
    load_dotenv(dotenv_path=".env.test", override=True)
elif env == "production":
    load_dotenv(dotenv_path=".env.production", override=True)
else:
    load_dotenv(dotenv_path=".env", override=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Email Verification
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", "24"))
    EMAIL_VERIFICATION_REQUIRED: bool = os.getenv("EMAIL_VERIFICATION_REQUIRED", "True").lower() == "true"
    
    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))


    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = os.getenv("SMTP_PORT", "587")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() == "true"


    # Frontend URL (for email verification links)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000/auth")
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    TESTING: bool = os.getenv("TESTING", "False").lower() == "true"
    
    class Config:
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate DATABASE_URL exists
if not settings.DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set. Please check your .env file or environment variables."
    )