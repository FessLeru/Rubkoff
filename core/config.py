from typing import List, Optional
import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from pydantic import Field, validator

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings with production-ready validation"""
    # Bot settings
    BOT_TOKEN: str = Field(..., description="Telegram bot token")
    ADMIN_IDS: str = Field(..., description="Comma-separated list of admin user IDs")
    NOTIFICATION_CHAT_ID: Optional[int] = None

    # OpenAI settings
    OPENAI_API_KEY: str = Field("", description="OpenAI API key")
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    # Database settings - production ready
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///data/rubkoff.db",
        description="Database connection URL"
    )

    # Website settings
    RUBKOFF_WORKS_URL: str = "https://rubkoff.ru/nashi-raboty/"
    COMPANY_WEBSITE: str = "https://rubkoff.ru"

    # Mini App settings - required for production
    MINI_APP_URL: str = Field("https://rubkoff.com", description="Mini app URL")
    API_BASE_URL: str = Field("https://rubkoff.com/api", description="API base URL")
    

    # Application settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Formatting settings
    AREA_SYMBOL: str = "м²"

    # Broadcast settings
    MAX_BROADCAST_CHUNK_SIZE: int = 30
    BROADCAST_DELAY: float = 0.5

    # Environment detection
    DOCKER_ENV: bool = Field(False, description="Whether running in Docker")

    _admin_ids: List[int] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Detect Docker environment
        self.DOCKER_ENV = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_ENV') == 'true'
        
        # Convert comma-separated IDs to list of integers
        try:
            self._admin_ids = [
                int(id.strip())
                for id in self.ADMIN_IDS.split(",")
                if id.strip()
            ] if self.ADMIN_IDS else []
            logger.info(f"Loaded admin IDs: {self._admin_ids}")
        except ValueError as e:
            logger.error(f"Error converting admin IDs: {e}. Using empty list.")
            self._admin_ids = []
        
        # Validate production settings
        self._validate_production_settings()
        
        # Log configuration status
        self._log_configuration_status()

    def _validate_production_settings(self):
        """Validate settings for production deployment"""
        # Validate critical settings
        if not self.OPENAI_API_KEY:
            logger.warning("⚠️  OPENAI_API_KEY not set - GPT features will be disabled")

    def _log_configuration_status(self):
        """Log configuration status"""
        logger.info(f"🔧 Configuration loaded:")
        logger.info(f"   Environment: {'Docker' if self.DOCKER_ENV else 'Local'}")
        logger.info(f"   Debug: {self.DEBUG}")
        logger.info(f"   Database: {self.DATABASE_URL}")
        logger.info(f"   Mini App URL: {self.MINI_APP_URL}")
        logger.info(f"   API Base URL: {self.API_BASE_URL}")

    @property
    def admin_ids(self) -> List[int]:
        return self._admin_ids

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self._admin_ids

    # Dynamic URL support for different environments
    @property 
    def effective_mini_app_url(self) -> str:
        """Get effective mini app URL based on environment"""
        return self.MINI_APP_URL
    
    @property
    def effective_api_base_url(self) -> str:
        """Get effective API base URL based on environment"""
        return self.API_BASE_URL

    @validator("ADMIN_IDS", pre=True)
    def parse_admin_ids(cls, v):
        """Parse admin IDs from string"""
        if isinstance(v, str):
            # Keep as string for field definition, but validate it's parseable
            try:
                [int(x.strip()) for x in v.split(",") if x.strip()]
                return v
            except ValueError:
                raise ValueError("ADMIN_IDS must be comma-separated integers")
        return v

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate database URL"""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        return v

    def check_readiness(self) -> bool:
        """Check if configuration is ready for deployment"""
        issues = []
        
        # Check required tokens
        if not self.BOT_TOKEN:
            issues.append("BOT_TOKEN is not set")
        
        if not self.ADMIN_IDS:
            issues.append("ADMIN_IDS is not set")
        
        if issues:
            logger.error("❌ Configuration issues:")
            for issue in issues:
                logger.error(f"   - {issue}")
            return False
        
        logger.info("✅ Configuration is ready for deployment")
        return True

    class Config:
        env_file = ".env"
        case_sensitive = True
        validate_assignment = True

# Create global config instance
config = Settings()

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging with proper file handling
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    ]
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger.info("✅ Configuration loaded successfully") 