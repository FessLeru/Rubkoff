import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_admin_panel_keyboard, get_back_to_admin_keyboard
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

# Create router for admin panel handlers
router = Router()


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle admin panel button click"""
    try:
        user_id = callback.from_user.id if callback.from_user else None
        logger.info(f"Processing admin panel access for user {user_id}")
        
        if not callback.from_user:
            logger.warning("No user information in callback")
            await callback.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            logger.warning(f"Unauthorized admin panel access attempt by user {callback.from_user.id}")
            await callback.answer("❌ У вас нет прав на доступ к панели администратора")
            return

        await callback.message.edit_text(
            "🔐 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        logger.info(f"Admin panel opened for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin panel for user {callback.from_user.id if callback.from_user else 'unknown'}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при открытии панели администратора")


@router.callback_query(F.data == "admin:back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to admin panel"""
    await state.clear()
    await callback.message.edit_text(
        "🔐 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()
