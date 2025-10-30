"""
Error handling utilities for production mode
"""
import logging
import functools
from typing import Optional, Callable, Any
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Update, Message, CallbackQuery
from core.config import config

logger = logging.getLogger(__name__)

class BotError(Exception):
    """Base exception for bot errors"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or "Произошла ошибка. Попробуйте позже."

class GPTError(BotError):
    """GPT service related errors"""
    pass

class DatabaseError(BotError):
    """Database related errors"""
    pass


def handle_gpt_error(e: OpenAIError) -> GPTError:
    """Convert OpenAI errors to GPTError"""
    error_map = {
        "invalid_request_error": "Некорректный запрос к GPT",
        "authentication_error": "Ошибка аутентификации GPT",
        "rate_limit_error": "Превышен лимит запросов к GPT",
        "api_error": "Ошибка API GPT",
    }
    error_type = getattr(e, "type", "api_error")
    user_msg = "Извините, сервис рекомендаций временно недоступен. Попробуйте позже."
    return GPTError(
        message=f"GPT error: {error_map.get(error_type, str(e))}",
        user_message=user_msg
    )

def handle_db_error(e: SQLAlchemyError) -> DatabaseError:
    """Convert SQLAlchemy errors to DatabaseError"""
    return DatabaseError(
        message=f"Database error: {str(e)}",
        user_message="Произошла ошибка при работе с базой данных. Попробуйте позже."
    )

def handle_telegram_error(e: TelegramAPIError) -> BotError:
    """Convert Telegram API errors to BotError"""
    return BotError(
        message=f"Telegram error: {str(e)}",
        user_message="Ошибка при отправке сообщения. Попробуйте позже."
    )

def with_error_handling(error_message: str = "Operation failed"):
    """
    Decorator for handling errors in async functions
    
    Usage:
    @with_error_handling("Failed to process user request")
    async def my_function():
        ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except OpenAIError as e:
                error = handle_gpt_error(e)
                logger.error(f"{error_message}: {str(error)}", exc_info=True)
                if not config.MOCK_MODE:  # Only raise in production
                    raise error
                return None  # Fallback to mock in development
            except SQLAlchemyError as e:
                error = handle_db_error(e)
                logger.error(f"{error_message}: {str(error)}", exc_info=True)
                raise error
            except TelegramAPIError as e:
                error = handle_telegram_error(e)
                logger.error(f"{error_message}: {str(error)}", exc_info=True)
                raise error
            except Exception as e:
                logger.error(f"Unexpected {error_message}: {str(e)}", exc_info=True)
                raise BotError(
                    message=f"Unexpected error: {str(e)}",
                    user_message="Произошла непредвиденная ошибка. Попробуйте позже."
                )
        return wrapper
    return decorator

async def handle_update_error(update: Update, error: Exception) -> None:
    """Handle errors that occur during update processing"""
    try:
        # Log the error
        logger.error(f"Error processing update {update.update_id}: {error}", exc_info=True)
        
        # Try to send error message to user
        user_id = None
        if isinstance(update, Message):
            user_id = update.from_user.id
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id
        elif hasattr(update, 'message') and update.message:
            user_id = update.message.from_user.id
        elif hasattr(update, 'callback_query') and update.callback_query:
            user_id = update.callback_query.from_user.id
        
        if user_id:
            error_message = "Произошла ошибка при обработке запроса. Попробуйте позже."
            
            # Try to send error message
            try:
                from aiogram import Bot
                from core.config import config
                
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(user_id, error_message)
                await bot.session.close()
            except Exception as send_error:
                logger.error(f"Failed to send error message to user {user_id}: {send_error}")
        
        # Notify admin about the error
        try:
            from core.config import config
            if config.NOTIFICATION_CHAT_ID:
                from aiogram import Bot
                
                bot = Bot(token=config.BOT_TOKEN)
                admin_message = (
                    f"🚨 <b>Bot Error</b>\n\n"
                    f"Update ID: {update.update_id}\n"
                    f"User: {user_id}\n"
                    f"Error: {str(error)}"
                )
                await bot.send_message(config.NOTIFICATION_CHAT_ID, admin_message)
                await bot.session.close()
        except Exception as admin_error:
            logger.error(f"Failed to notify admin about error: {admin_error}")
    
    except Exception as handler_error:
        logger.error(f"Error in error handler: {handler_error}", exc_info=True)

async def graceful_shutdown(app: Any = None) -> None:
    """Gracefully shutdown all services"""
    logger.info("Shutting down services...")
    try:
        # Close database connections
        from core.db import db
        await db.close_connections()
        logger.info("Database connections closed")
        
        # Close any other resources
        if app and hasattr(app, 'state'):
            if hasattr(app.state, 'gpt_service'):
                await app.state.gpt_service.close()
            if hasattr(app.state, 'bot'):
                await app.state.bot.session.close()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
    finally:
        logger.info("Shutdown complete") 