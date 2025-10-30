from typing import AsyncGenerator, Optional
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from core.config import config
from models.models import Base

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager"""
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session: Optional[sessionmaker] = None

    async def init_db(self) -> None:
        """Initialize database connection and create tables"""
        try:
            self.engine = create_async_engine(
                config.DATABASE_URL,
                echo=config.DEBUG
            )
            
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        if not self.async_session:
            await self.init_db()
            
        session: AsyncSession = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

    async def check_connection(self) -> bool:
        """Check if database connection is working"""
        try:
            async with self.get_db_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    async def get_table_count(self, table_name: str) -> int:
        """Get number of records in specified table"""
        try:
            async with self.get_db_session() as session:
                result = await session.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to get count for table {table_name}: {e}")
            return 0

# Create global database instance
db = Database() 