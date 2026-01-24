"""
Configuration management using Pydantic Settings.
All environment variables are loaded and validated here.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Real Estate Voice AI"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: Optional[str] = None
    # Format: postgresql+asyncpg://user:password@localhost:5432/voiceai
    # Optional for deployment testing - add PostgreSQL service in Railway for production

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Exotel (we'll use these in Module 3)
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_VIRTUAL_NUMBER: str = ""
    EXOTEL_EXOPHLO_ID: str = ""

    # Our Server Base URL (for webhooks)
    OUR_BASE_URL: str = "http://localhost:8000"  # Update with actual domain/ngrok URL

    # AI Services (we'll use these in Module 4-6)
    DEEPGRAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # Email Configuration (for lead monitoring)
    EMAIL_IMAP_HOST: str = "imap.gmail.com"  # Gmail IMAP server
    EMAIL_IMAP_PORT: int = 993
    EMAIL_ADDRESS: str = ""  # Your email address
    EMAIL_PASSWORD: str = ""  # App password for Gmail
    EMAIL_POLL_INTERVAL_SECONDS: int = 30  # Check email every 30 seconds
    EMAIL_FOLDER: str = "INBOX"  # Email folder to monitor
    EMAIL_MARK_AS_READ: bool = True  # Mark processed emails as read

    # WebSocket
    WEBSOCKET_ENDPOINT_PATH: str = "/media"

    # Call Settings
    MAX_CALL_DURATION_MINUTES: int = 10
    CALLING_HOURS_START: int = 10  # 10 AM
    CALLING_HOURS_END: int = 19    # 7 PM
    MAX_CONCURRENT_CALLS: int = 10

    # Email Lead Auto-Calling
    EMAIL_LEADS_AUTO_CALL: bool = True  # Enable/disable auto-calling for email leads
    EMAIL_LEADS_MAX_RETRY_ATTEMPTS: int = 3
    EMAIL_LEADS_RETRY_DELAY_HOURS: int = 2
    EMAIL_LEADS_DEFAULT_CAMPAIGN_NAME: str = "Email Leads - Auto"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Create a singleton instance
settings = Settings()
