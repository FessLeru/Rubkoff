import logging
from typing import Optional, Dict, Any
from datetime import datetime
from aiogram import Bot
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User, Statistic, Admin
from app.core.config import config

logger = logging.getLogger(__name__)

async def is_admin(user_id: int, session: AsyncSession) -> bool:
    """Check if user is admin using both config and database"""
    try:
        # First check config for fast response
        if user_id in config.admin_ids:
            # If in config, ensure user is in admin table
            result = await session.execute(
                select(Admin).where(Admin.user_id == user_id)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                # Add to admin table if not present
                admin = Admin(user_id=user_id)
                session.add(admin)
                await session.commit()
                logger.info(f"Added user {user_id} to admin table")
            
            return True
            
        # If not in config, check if in database (legacy admins)
        result = await session.execute(
            select(Admin).where(Admin.user_id == user_id)
        )
        return bool(result.scalar_one_or_none())
        
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}")
        # Default to config check in case of database error
        return user_id in config.admin_ids

async def register_or_update_user(tg_user: TgUser, session: AsyncSession) -> Optional[User]:
    """Register a new user or update existing user information"""
    if not tg_user:
        logger.error("Cannot register user: tg_user is None")
        return None
        
    try:
        result = await session.execute(
            select(User).where(User.user_id == tg_user.id)
        )
        user = result.scalars().first()
        
        if user:
            # Update existing user
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.last_activity = datetime.utcnow()
            user.language_code = tg_user.language_code
            user.is_blocked = False
        else:
            # Create new user
            user = User(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code
            )
            session.add(user)
            
            # Record statistic for new user
            stat = Statistic(user_id=tg_user.id, action="registered")
            session.add(stat)
            
        await session.commit()
        return user
    except Exception as e:
        logger.error(f"Error registering user {tg_user.id}: {e}", exc_info=True)
        await session.rollback()
        return None

async def log_user_action(
    user_id: int,
    action: str,
    house_id: Optional[int] = None,
    session: AsyncSession = None
) -> None:
    """Log user action for statistics"""
    if not session:
        logger.warning(f"Cannot log action '{action}' for user {user_id}: No session provided")
        return
        
    try:
        stat = Statistic(
            user_id=user_id,
            action=action,
            house_id=house_id
        )
        session.add(stat)
        await session.commit()
        logger.debug(f"Logged action '{action}' for user {user_id}")
    except Exception as e:
        logger.error(f"Error logging user action '{action}' for user {user_id}: {e}", exc_info=True)
        await session.rollback()

async def notify_house_selection(
    bot: Bot,
    user: TgUser,
    house: Dict[str, Any],
    session: AsyncSession = None
) -> bool:
    """Send notification about house selection to notification chat"""
    if not config.NOTIFICATION_CHAT_ID:
        logger.warning("Notification chat ID not configured, skipping notification")
        return False
    
    try:
        # Build notification message
        username = f"@{user.username}" if user.username else f"{user.first_name} {user.last_name or ''}"
        user_id = user.id
        
        message = (
            f"🏠 Пользователю {username} (ID: {user_id}) подобран дом:\n\n"
            f"🔑 {house['name']}\n"
            f"📐 Площадь: {house['area']} м²\n"
        )
        
        if house['bedrooms']:
            message += f"🛏️ Спален: {house['bedrooms']}\n"
        if house['bathrooms']:
            message += f"🚿 Санузлов: {house['bathrooms']}\n"
        if house['floors']:
            message += f"⬆️ Этажей: {house['floors']}\n"
            
        message += f"\n🌐 {house['url']}"
        
        # Send notification with image if available
        if house['image_url']:
            await bot.send_photo(
                chat_id=config.NOTIFICATION_CHAT_ID,
                photo=house['image_url'],
                caption=message
            )
        else:
            await bot.send_message(
                chat_id=config.NOTIFICATION_CHAT_ID,
                text=message
            )
        
        # Log action
        if session:
            await log_user_action(
                user_id=user_id,
                action="house_selected",
                house_id=house['id'],
                session=session
            )
        
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
        return False 