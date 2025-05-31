import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.core.config import config
from app.core.db import db
from app.bot import main_router, admin_router
from app.bot.middlewares import DatabaseMiddleware, ThrottlingMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()  # Add console output
    ]
)

# Set more detailed logging for specific modules
logging.getLogger('app.core.config').setLevel(logging.DEBUG)
logging.getLogger('app.bot.handlers').setLevel(logging.DEBUG)
logging.getLogger('app.bot.admin_handlers').setLevel(logging.DEBUG)
logging.getLogger('app.services.gpt_service').setLevel(logging.DEBUG)
logging.getLogger('app.services.scraper').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        # Initialize database
        logger.info("Initializing database...")
        await db.init_db()
        logger.info("Database initialized successfully")
        
        # Register middlewares
        logger.info("Registering middlewares...")
        dp.message.middleware(DatabaseMiddleware())
        dp.callback_query.middleware(DatabaseMiddleware())
        dp.message.middleware(ThrottlingMiddleware())
        dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))
        logger.info("Middlewares registered successfully")
        
        # Register routers
        logger.info("Registering routers...")
        dp.include_router(admin_router)
        dp.include_router(main_router)
        logger.info("Routers registered successfully")
        
        # Start polling
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot stopped due to error: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")
