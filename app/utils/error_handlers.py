"""Error handling utilities"""
import logging
from typing import Optional, Callable, Awaitable, Any
from functools import wraps
import traceback

from aiogram import types
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAIError

from app.core.config import config
from app.utils.text_utils import format_error
from app.utils.constants import ERROR_GENERAL

logger = logging.getLogger(__name__)

def error_handler(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Decorator for handling errors in handlers"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Optional[Any]:
        try:
            return await func(*args, **kwargs)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error in {func.__name__}: {e}", exc_info=True)
            # Try to get message object from args
            message = next((arg for arg in args if isinstance(arg, types.Message)), None)
            if message:
                await message.answer(format_error(ERROR_GENERAL))
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
            message = next((arg for arg in args if isinstance(arg, types.Message)), None)
            if message:
                await message.answer(format_error(ERROR_GENERAL))
        except OpenAIError as e:
            logger.error(f"OpenAI API error in {func.__name__}: {e}", exc_info=True)
            message = next((arg for arg in args if isinstance(arg, types.Message)), None)
            if message:
                await message.answer(format_error("Ошибка при обработке запроса к GPT. Попробуйте позже."))
        except Exception as e:
            logger.error(
                f"Unexpected error in {func.__name__}: {e}\n"
                f"Traceback:\n{traceback.format_exc()}",
                exc_info=True
            )
            message = next((arg for arg in args if isinstance(arg, types.Message)), None)
            if message:
                await message.answer(format_error(ERROR_GENERAL))
            
            # Notify admins about error if notification chat is set
            if config.NOTIFICATION_CHAT_ID:
                try:
                    bot = message.bot if message else args[0].bot
                    await bot.send_message(
                        config.NOTIFICATION_CHAT_ID,
                        f"❌ Error in {func.__name__}:\n"
                        f"```\n{traceback.format_exc()}\n```",
                        parse_mode="Markdown"
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to notify admins: {notify_error}")
        return None
    return wrapper

async def handle_update_error(update: types.Update, exception: Exception) -> bool:
    """Global error handler for updates"""
    logger.error(
        f"Error handling update {update.update_id}:\n"
        f"{traceback.format_exc()}",
        exc_info=True
    )
    
    try:
        # Try to get chat id and send error message
        if update.message:
            chat_id = update.message.chat.id
            bot = update.message.bot
        elif update.callback_query:
            chat_id = update.callback_query.message.chat.id
            bot = update.callback_query.message.bot
        else:
            return True
            
        await bot.send_message(
            chat_id,
            format_error(ERROR_GENERAL)
        )
        
        # Notify admins
        if config.NOTIFICATION_CHAT_ID:
            await bot.send_message(
                config.NOTIFICATION_CHAT_ID,
                f"❌ Error handling update {update.update_id}:\n"
                f"```\n{traceback.format_exc()}\n```",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
    
    return True 