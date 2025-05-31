"""Middlewares for the bot"""
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import db
from app.utils.db_utils import get_user_by_id, create_user, update_user_activity
from app.utils.text_utils import format_error
from app.utils.error_handlers import handle_update_error
from app.utils.constants import ERROR_GENERAL

logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    """Middleware for database session management and user tracking"""
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        # Create database session
        async with db.get_db_session() as session:
            data["session"] = session
            
            # Process user if present
            if user:
                try:
                    # Try to get existing user
                    db_user = await get_user_by_id(session, user.id)
                    
                    if not db_user:
                        # Create new user
                        db_user = await create_user(
                            session=session,
                            user_id=user.id,
                            username=user.username,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            language_code=user.language_code
                        )
                        logger.info(f"New user registered: {user.id}")
                    else:
                        # Update user's activity
                        await update_user_activity(session, user.id)
                        
                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {e}", exc_info=True)
            
            try:
                return await handler(event, data)
            except Exception as e:
                logger.error(f"Error in handler: {e}", exc_info=True)
                await handle_update_error(event, e)
                return None

class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting"""
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_request: Dict[int, datetime] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Get user ID from event
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id:
            now = datetime.now()
            if user_id in self.last_request:
                diff = (now - self.last_request[user_id]).total_seconds()
                if diff < self.rate_limit:
                    if isinstance(event, CallbackQuery):
                        await event.answer("Пожалуйста, подождите немного перед следующим действием")
                    return None

            self.last_request[user_id] = now

        return await handler(event, data) 