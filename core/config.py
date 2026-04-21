from pydantic_settings import BaseSettings
from typing import Optional, Any
from sqlalchemy import create_engine
import os


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_ignore_empty": True, "extra": "ignore"}

    # Application
    APP_NAME: str = "WhatsApp Platform Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://whatsapp_platform_mhnw_user:nComdm17QkuwCzuxi2sMjZrIbXXLV8FG@dpg-d7cbd05ckfvc7387lfog-a.oregon-postgres.render.com/whatsapp_platform_mhnw"

    # Security
    SECRET_KEY: str = "your-super-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # WhatsApp API
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None

    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # Engine

    # Bulk Messaging Settings
    SESSION_MESSAGE_LIMIT: int = 1250
    MIN_DELAY: int = 3
    MAX_DELAY: int = 7
    WARM_MIN_DELAY: int = 8
    WARM_MAX_DELAY: int = 15
    MAX_RETRY: int = 3

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Google Sheets API
    GOOGLE_SHEETS_CLIENT_ID: Optional[str] = None
    GOOGLE_SHEETS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_SHEETS_REDIRECT_URI: Optional[str] = None
    GOOGLE_SHEETS_SCOPES: str = "https://www.googleapis.com/auth/spreadsheets.readonly"
    GOOGLE_SHEETS_WEBHOOK_SECRET: Optional[str] = None

    # WhatsApp Engine
    WHATSAPP_ENGINE_URL: str = os.getenv("WHATSAPP_ENGINE_URL", "http://localhost:3002")

    @property
    def WHATSAPP_ENGINE_BASE_URL(self) -> str:
        # ROBUST: Ensure URL is stripped of any hidden newlines or whitespace
        return (self.WHATSAPP_ENGINE_URL or "").strip()

    _engine: Optional[Any] = None

    @property
    def engine(self):
        """Database engine with connection pool settings and auto-fix for URL typos"""
        if self._engine is not None:
            return self._engine
            
        db_url = self.DATABASE_URL
        
        # 🔥 ROBUST FIX: Correct legacy 'postgres://' or truncated 'stgresql://'
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        elif db_url and db_url.startswith("stgresql://"):
            db_url = "po" + db_url
            
        self._engine = create_engine(
            db_url,
            pool_size=25,  # Production-optimized: not configurable via env
            max_overflow=25,  # Production-optimized: not configurable via env
            pool_timeout=60,  # Increased from 30 to 60 seconds for high load scenarios
            pool_recycle=3600,  # Increased from 1800 to 3600 (1 hour)
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,  # Reduced from 30 to 10 seconds
                "sslmode": "require",
                "application_name": "whatsapp_platform"
            }
        )
        
        # Log pool settings for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 Database engine created with pool_size=25, max_overflow=25")
        
        return self._engine

    def recreate_engine(self):
        """Force recreation of database engine with new settings"""
        if self._engine is not None:
            try:
                self._engine.dispose()
                logger = logging.getLogger(__name__)
                logger.info("🔄 Disposed old database engine")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Error disposing engine: {e}")
        self._engine = None
        return self.engine



settings = Settings()