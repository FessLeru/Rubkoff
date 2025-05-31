import asyncio
import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
import sqlite3
from datetime import datetime

from app.core.config import config

logger = logging.getLogger(__name__)

class DatabaseMigration:
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None

    async def init_engine(self) -> None:
        """Initialize database engine"""
        self.engine = create_async_engine(config.DATABASE_URL)

    async def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table"),
                    {"table": table_name}
                )
                return bool(result.scalar())
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    async def get_table_columns(self, table_name: str) -> list[Tuple[str, str]]:
        """Get columns information for a table"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text("PRAGMA table_info(:table)"),
                    {"table": table_name}
                )
                return [(row[1], row[2]) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting table columns: {e}")
            return []

    async def migrate(self) -> bool:
        """Execute database migration"""
        logger.info("Starting database migration...")
        
        try:
            await self.init_engine()
            
            # Check if admins table exists
            if not await self.check_table_exists("admins"):
                logger.info("Admins table doesn't exist yet. No migration needed.")
                return True
            
            # Check if the column exists
            columns = await self.get_table_columns("admins")
            has_superadmin_column = any(col[0] == "is_superadmin" for col in columns)
            
            if not has_superadmin_column:
                logger.info("The is_superadmin column doesn't exist. No migration needed.")
                return True
            
            # Execute migration in transaction
            async with self.engine.begin() as conn:
                # Create new table
                await conn.execute(text("""
                    CREATE TABLE admins_new (
                        id INTEGER PRIMARY KEY,
                        user_id BIGINT UNIQUE NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Copy data
                await conn.execute(text("""
                    INSERT INTO admins_new (id, user_id, added_at)
                    SELECT id, user_id, added_at FROM admins
                """))
                
                # Drop old table
                await conn.execute(text("DROP TABLE admins"))
                
                # Rename new table
                await conn.execute(text("ALTER TABLE admins_new RENAME TO admins"))
            
            logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False
        finally:
            if self.engine:
                await self.engine.dispose()

async def run_migration() -> None:
    """Run database migration"""
    migration = DatabaseMigration()
    success = await migration.migrate()
    
    if not success:
        logger.error("Migration failed")
        raise SystemExit(1)

def migrate_database():
    """Migrate the database schema"""
    try:
        # Connect to the database
        conn = sqlite3.connect('houses.db')
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if created_at column exists
        if 'created_at' not in column_names:
            logger.info("Adding created_at column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            logger.info("Added created_at column")
        
        # Check if last_active column exists
        if 'last_active' not in column_names:
            logger.info("Adding last_active column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            logger.info("Added last_active column")
        
        # Check if language_code column exists
        if 'language_code' not in column_names:
            logger.info("Adding language_code column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN language_code TEXT DEFAULT 'ru'
            """)
            logger.info("Added language_code column")
        
        # Update existing rows with current timestamp if needed
        cursor.execute("""
            UPDATE users 
            SET created_at = CURRENT_TIMESTAMP 
            WHERE created_at IS NULL
        """)
        
        cursor.execute("""
            UPDATE users 
            SET last_active = CURRENT_TIMESTAMP 
            WHERE last_active IS NULL
        """)
        
        # Commit changes
        conn.commit()
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise
    
    finally:
        # Close connection
        if conn:
            conn.close()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_migration())
    migrate_database() 