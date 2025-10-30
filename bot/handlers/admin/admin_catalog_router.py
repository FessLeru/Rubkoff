"""
Роутер для управления каталогом домов
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_back_to_admin_keyboard
from services.scraper import parse_houses
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

# Create router for admin catalog handlers
router = Router()


@router.callback_query(F.data == "admin:refresh")
async def refresh_catalog(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh houses catalog"""
    if not callback.from_user:
        await callback.answer("Error: User not found")
        return

    try:
        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.message.edit_text(
            "🔄 Обновление каталога домов...\n"
            "Пожалуйста, подождите."
        )

        houses_count = await parse_houses(session)
        
        await callback.message.edit_text(
            f"✅ Каталог обновлен\n\n"
            f"Загружено домов: {houses_count}",
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error refreshing catalog: {e}")
        await callback.answer("Произошла ошибка")
