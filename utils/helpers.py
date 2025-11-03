import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from aiogram import Bot
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import User, Statistic, Admin
from core.config import config
from services.recommendation_service import recommendation_service

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
            
        await session.flush()
        return user
    except Exception as e:
        logger.error(f"Error registering user {tg_user.id}: {e}", exc_info=True)
        await session.rollback()
        # Try to fetch existing user after rollback
        try:
            result = await session.execute(
                select(User).where(User.user_id == tg_user.id)
            )
            return result.scalars().first()
        except:
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

async def save_user_recommendations(
    user_id: int,
    houses: List[Dict[str, Any]],
    criteria: Optional[Dict[str, Any]] = None,
    session: AsyncSession = None
) -> bool:
    """
    Save user recommendations from bot to database
    
    Args:
        user_id: Telegram user ID
        houses: List of house data with IDs and scores
        criteria: User criteria used for recommendation
        session: Database session
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not session:
        logger.error("No database session provided for saving recommendations")
        return False
        
    try:
        house_ids = []
        scores = []
        reasons = []
        
        for house in houses:
            house_ids.append(house.get('id'))
            scores.append(house.get('recommendation_score', 85))
            reasons.append(house.get('match_reasons', []))
        
        # Save to database using recommendation service
        success = await recommendation_service.save_recommendations(
            user_id=user_id,
            house_ids=house_ids,
            criteria=criteria,
            scores=scores,
            reasons=reasons,
            session=session
        )
        
        if success:
            logger.info(f"Saved {len(house_ids)} recommendations for user {user_id}")
        else:
            logger.error(f"Failed to save recommendations for user {user_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error saving recommendations for user {user_id}: {e}", exc_info=True)
        return False

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
            f"💰 Цена: {house.get('price', 'Не указана')} ₽\n"
            f"📐 Площадь: {house['area']} м²\n"
        )
        
        if house.get('bedrooms'):
            message += f"🛏️ Спален: {house['bedrooms']}\n"
        if house.get('bathrooms'):
            message += f"🚿 Санузлов: {house['bathrooms']}\n"
        if house.get('floors'):
            message += f"⬆️ Этажей: {house['floors']}\n"
            
        message += f"\n🌐 {house['url']}"
        
        # Send only text notification (no photo)
        await bot.send_message(
            chat_id=config.NOTIFICATION_CHAT_ID,
            text=message
        )
        
        logger.info(f"Sent house selection notification for user {user_id}")
        
        # Log action
        if session:
            await log_user_action(
                user_id=user_id,
                action="house_selected",
                house_id=house.get('id'),
                session=session
            )
        
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
        return False 