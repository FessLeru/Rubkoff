"""
Роутер для обработки опроса пользователей
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services.scraper import get_all_houses
from services.gpt_service import chat_with_gpt, find_best_house
from bot.keyboards import get_house_result_keyboard
from bot.states import SurveyStates
from utils.helpers import log_user_action, register_or_update_user
from core.config import config
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Start the house selection survey"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "survey_start", session=session)

        # Start survey with questions
        await state.set_state(SurveyStates.in_progress)
        
        houses = await get_all_houses(session)
        if not houses:
            await callback.message.answer("К сожалению, каталог домов пуст. Попробуйте позже.")
            await callback.answer()
            return

        house_info = "\n\n".join([
            f"Дом {house['name']}: {house.get('price', 0)} руб., {house.get('area', 0)} м², {house.get('bedrooms', 0)} спален, {house.get('bathrooms', 0)} ванных, описание: {(house.get('description') or '')[:200]}"
            for house in houses[:10]
        ])

        system_message = {
            "role": "system",
            "content": (
                "Ты — опытный консультант по загородной недвижимости от компании Rubkoff. "
                "У тебя 10+ лет опыта. Ты помогаешь клиентам найти идеальный дом.\n\n"
                "СТИЛЬ ОБЩЕНИЯ:\n"
                "- Дружелюбный и профессиональный, но не официальный\n"
                "- Используй эмодзи умеренно для живости\n"
                "- Показывай экспертность через детали\n"
                "- Давай полезные советы по ходу беседы\n\n"
                "ЗАДАЧИ:\n"
                "1. Задай 6-8 вопросов о предпочтениях клиента\n"
                "2. Спрашивай по одному вопросу за раз, используй формат (1/8), (2/8) и т.д.\n"
                "3. Вопросы: бюджет, площадь, этажность, стиль, материалы, особенности, расположение\n"
                "4. После всех вопросов скажи 'Отлично! Подберу для вас идеальные варианты' и предложи 2-3 дома\n\n"
                f"Доступные дома для подбора:\n{house_info}\n\n"
                "НАЧНИ ПРЯМО СЕЙЧАС с первого вопроса про бюджет. Не спрашивай разрешения."
            )
        }

        conversation_history = [system_message]
        await state.update_data(
            conversation_history=conversation_history,
            timestamp=datetime.utcnow().isoformat()
        )

        gpt_response = await chat_with_gpt("Начать опрос", conversation_history, houses)
        if not gpt_response:
            await callback.message.answer("Произошла ошибка при генерации вопроса. Попробуйте позже.")
            await callback.answer()
            return

        assistant_message = {"role": "assistant", "content": gpt_response}
        conversation_history.append(assistant_message)
        await state.update_data(conversation_history=conversation_history)

        await callback.message.answer(gpt_response)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in start_survey: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await callback.answer()


@router.callback_query(F.data == "restart_survey")
async def restart_survey(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Restart the survey"""
    if callback.from_user:
        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "survey_restart", session=session)
    
    await state.set_state(SurveyStates.waiting_for_start)
    from bot.handlers.user.start_router import cmd_start
    await cmd_start(callback.message, state, session)
    await callback.answer()


@router.message(SurveyStates.in_progress)
async def process_survey_step(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process user responses during survey"""
    try:
        if not message.from_user:
            return

        await register_or_update_user(message.from_user, session)
        await log_user_action(message.from_user.id, "survey_response", session=session)

        # Use real GPT service
        data = await state.get_data()
        conversation_history = data.get("conversation_history", [])
        houses = await get_all_houses(session)

        if not houses:
            await message.answer("К сожалению, каталог домов пуст. Попробуйте позже.")
            return

        user_message = {"role": "user", "content": message.text}
        conversation_history.append(user_message)

        gpt_response = await chat_with_gpt(message.text, conversation_history, houses)
        if not gpt_response:
            await message.answer("Произошла ошибка при обработке ответа. Попробуйте позже.")
            return

        assistant_message = {"role": "assistant", "content": gpt_response}
        conversation_history.append(assistant_message)
        await state.update_data(conversation_history=conversation_history)

        if is_survey_complete(gpt_response):
            await state.set_state(SurveyStates.finished)
            
            # Сохранить рекомендации GPT в базу данных
            await save_gpt_recommendations(message.from_user.id, gpt_response, houses, state, session)
            
            kb = InlineKeyboardBuilder()
            kb.button(text="🏠 Посмотреть подобранные дома", web_app={"url": f"{config.effective_mini_app_url}?user_id={message.from_user.id}"})
            kb.button(text="🔄 Пройти опрос заново", callback_data="restart_survey")
            kb.adjust(1)
            await message.answer(
                "✅ <b>Отлично! Я подобрал для вас лучшие варианты!</b>\n\n"
                "Нажмите кнопку ниже, чтобы посмотреть подобранные дома с полным описанием.",
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )
        else:
            await message.answer(gpt_response)

    except Exception as e:
        logger.error(f"Error in process_survey_step: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


def is_survey_complete(response: str) -> bool:
    """Check if survey is complete based on GPT response"""
    completion_keywords = [
        "опрос завершен",
        "все вопросы заданы",
        "достаточно информации",
        "подберу",
        "подобрал",
        "подобрала",
        "анализирую ваши ответы",
        "поиск подходящих вариантов",
        "идеальные варианты",
        "нашел несколько вариантов",
        "нашла несколько вариантов"
    ]
    
    response_lower = response.lower()
    return any(keyword in response_lower for keyword in completion_keywords)


async def save_gpt_recommendations(
    user_id: int, 
    gpt_response: str, 
    all_houses: list,
    state: FSMContext,
    session: AsyncSession
) -> None:
    """Извлечь номера домов из ответа GPT и сохранить рекомендации"""
    try:
        import re
        from utils.helpers import save_user_recommendations
        
        # Извлечь все номера после "Дом" или "ID" из ответа GPT
        pattern = r'(?:Дом|ID)\s*(\d+)'
        house_ids = re.findall(pattern, gpt_response)
        
        if not house_ids:
            # Если не нашли номера, сохраним первый дом
            logger.warning("No house IDs found in GPT response, using first house")
            if all_houses:
                house_ids = [str(all_houses[0]['id'])]
        
        # Получить дома по ID
        recommended_houses = []
        for house_id_str in house_ids[:3]:  # Максимум 3 дома
            try:
                house_id = int(house_id_str)
                house = next((h for h in all_houses if h['id'] == house_id), None)
                if house:
                    recommended_houses.append(house)
            except ValueError:
                continue
        
        if recommended_houses:
            # Сохранить рекомендации
            data = await state.get_data()
            criteria = data.get("conversation_history", [])
            await save_user_recommendations(
                user_id=user_id,
                houses=recommended_houses,
                criteria={"conversation_history": criteria, "gpt_response": gpt_response},
                session=session
            )
            logger.info(f"Saved {len(recommended_houses)} recommendations for user {user_id}")
        else:
            logger.error(f"No valid houses found for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error saving GPT recommendations: {e}", exc_info=True)
