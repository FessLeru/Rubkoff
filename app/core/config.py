from typing import List, Optional
import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    # Bot settings
    BOT_TOKEN: str
    ADMIN_IDS: str = ""  # Will be converted to List[int] in __init__
    NOTIFICATION_CHAT_ID: Optional[int] = None

    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///houses.db"

    # Website settings
    RUBKOFF_URL: str = "https://rubkoff.ru/catalog/doma-v-prodazhe/"
    RUBKOFF_WORKS_URL: str = "https://rubkoff.ru/nashi-raboty/"
    COMPANY_NAME: str = "Rubkoff"
    COMPANY_WEBSITE: str = "https://rubkoff.ru"

    # Application settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bot.log"

    # Language settings
    DEFAULT_LANGUAGE: str = "ru"

    # Formatting settings
    CURRENCY_SYMBOL: str = "₽"
    AREA_SYMBOL: str = "м²"

    # Broadcast settings
    MAX_BROADCAST_CHUNK_SIZE: int = 30
    BROADCAST_DELAY: float = 0.5

    _admin_ids: List[int] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Convert comma-separated IDs to list of integers
        try:
            self._admin_ids = [
                int(id.strip())
                for id in self.ADMIN_IDS.split(',')
                if id.strip()
            ] if self.ADMIN_IDS else []
            logger.info(f"Loaded admin IDs: {self._admin_ids}")
        except ValueError as e:
            logger.error(f"Error converting admin IDs: {e}. Using empty list.")
            self._admin_ids = []

    @property
    def admin_ids(self) -> List[int]:
        return self._admin_ids

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self._admin_ids

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global config instance
config = Settings()
logger.info("Configuration loaded successfully") 