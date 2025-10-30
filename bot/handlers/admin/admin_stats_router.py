import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import User, Statistic
from bot.keyboards import get_back_to_admin_keyboard
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

# Create router for admin stats handlers
router = Router()


@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show bot statistics"""
    try:
        user_id = callback.from_user.id if callback.from_user else None
        logger.info(f"Processing stats request for user {user_id}")
        
        if not callback.from_user:
            logger.warning("No user information in callback")
            await callback.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            logger.warning(f"Unauthorized stats access attempt by user {callback.from_user.id}")
            await callback.answer("❌ Доступ запрещен")
            return

        # Get total users count
        total_users = await session.scalar(select(func.count(User.id)))

        # Get active users (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        active_users = await session.scalar(
            select(func.count(User.id))
            .where(User.last_activity >= day_ago)
        )

        # Get today's statistics
        today = datetime.utcnow().date()
        today_stats = await session.scalar(
            select(func.count(Statistic.id))
            .where(func.date(Statistic.timestamp) == today)
        )

        # Get houses count
        houses_count = await session.scalar(text("SELECT COUNT(*) FROM houses"))

        stats_text = (
            "📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"📱 Активных за 24 часа: {active_users}\n"
            f"📈 Действий за сегодня: {today_stats}\n"
            f"🏠 Домов в каталоге: {houses_count}"
        )

        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
        logger.info(f"Stats shown to admin {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error showing stats for user {callback.from_user.id if callback.from_user else 'unknown'}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при получении статистики")
