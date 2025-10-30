"""
Роутер для обработки результатов подбора домов
"""

from typing import Optional, Dict, Any, List
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from services.scraper import get_all_houses
from services.gpt_service import find_best_house
from bot.keyboards import get_house_result_keyboard
from bot.states import SurveyStates
from utils.helpers import log_user_action, register_or_update_user, notify_house_selection, save_user_recommendations
from core.config import config

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.callback_query(F.data == "show_result")
async def show_result(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Show recommended houses"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "show_result", session=session)

        await callback.message.answer("🔍 Анализирую ваши ответы и подбираю 3 идеальных дома...")

        # Use real GPT service
        data = await state.get_data()
        conversation_history = data.get("conversation_history", [])
        houses = await get_all_houses(session)

        if not houses:
            await callback.message.answer("К сожалению, каталог домов пуст. Попробуйте позже.")
            await callback.answer()
            return

        house_id = await find_best_house(conversation_history, houses)
        house = next((h for h in houses if h["id"] == house_id), None)

        if not house:
            await callback.message.answer("К сожалению, подходящий дом не найден. Попробуйте изменить критерии поиска.")
            await callback.answer()
            return

        message = format_house_message(house)
        
        # Simple keyboard for production mode
        keyboard = get_house_result_keyboard(callback.from_user.id)

        await callback.message.answer(
            f"✅ <b>Дом подобран!</b>\n\n{message}", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        # Send notifications to all admins (without photo)
        await notify_house_selection(
            bot=callback.bot,
            user=callback.from_user,
            house=house,
            session=session
        )
        
        # Save single recommendation to database for API access
        data = await state.get_data()
        criteria = data.get("conversation_history", [])
        await save_user_recommendations(
            user_id=callback.from_user.id,
            houses=[house],
            criteria={"conversation_history": criteria},
            session=session
        )

        await state.set_state(SurveyStates.finished)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_result: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await callback.answer()


@router.callback_query(F.data.startswith("mini_app_link:"))
async def mini_app_link(callback: CallbackQuery, session: AsyncSession):
    """Show mini app link for HTTP URLs (fallback when HTTPS not available)"""
    try:
        if callback.from_user:
            await register_or_update_user(callback.from_user, session)
            await log_user_action(callback.from_user.id, "mini_app_link", session=session)
        
        # Extract user_id from callback data
        user_id = callback.data.split(":")[1] if ":" in callback.data else callback.from_user.id
        
        # Create mini app URL
        mini_app_url = f"{config.effective_mini_app_url}?user_id={user_id}"
        
        message = (
            "🏠 <b>Мини-приложение Rubkoff</b>\n\n"
            f"🔗 <b>Ссылка:</b>\n<code>{mini_app_url}</code>\n\n"
            "📱 <i>Откройте ссылку в браузере для просмотра подобранного дома</i>\n\n"
            "⚠️ <i>Примечание: Для работы в Telegram требуется HTTPS. "
            "Сейчас доступно тестирование через браузер.</i>"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Подобрать другой дом", callback_data="restart_survey")
        kb.adjust(1)
        
        await callback.message.answer(message, reply_markup=kb.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in mini_app_link: {e}", exc_info=True)
        await callback.answer("Произошла ошибка")


def format_house_message(house: Dict[str, Any]) -> str:
    """Format house information for display"""
    message = (
        f"🏠 <b>{house['name']}</b>\n\n"
        f"💰 Цена: {house['price']:,.0f} ₽\n"
        f"📏 Площадь: {house['area']} м²\n"
    )
    
    if house.get('bedrooms'):
        message += f"🛏 Спален: {house['bedrooms']}\n"
    if house.get('bathrooms'):
        message += f"🚿 Санузлов: {house['bathrooms']}\n"
    if house.get('floors'):
        message += f"🏗 Этажей: {house['floors']}\n"
    
    if house.get('description'):
        message += f"\n📝 {house['description']}\n"
    
    message += f"\n🔗 <a href='{house['url']}'>Подробнее на сайте</a>"
    
    return message


