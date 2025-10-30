"""
Основной файл приложения
Импортирует и запускает бота из start_bot.py
"""

from bot.start_bot import main
import asyncio
import logging

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot stopped due to error: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")
