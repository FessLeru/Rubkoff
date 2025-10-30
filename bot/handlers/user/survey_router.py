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
from services.kafka_service import kafka_service
from bot.keyboards import get_house_result_keyboard
from bot.states import SurveyStates
from utils.helpers import log_user_action, register_or_update_user
from core.config import config

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
            f"Дом {house['name']}: {house['price']} руб., {house['area']} м², {house['bedrooms']} спален, {house['bathrooms']} ванных, описание: {house['description'][:200]}"
            for house in houses[:10]
        ])

        system_message = {
            "role": "system",
            "content": "Начни опрос клиента для подбора дома сразу с первого вопроса про бюджет. "
            "Используй формат (1/8). Не спрашивай разрешения начать опрос и не добавляй лишнего текста."
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
            
            # Отправить данные в Kafka
            await send_survey_to_kafka(message.from_user.id, state, houses)
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            kb = InlineKeyboardBuilder()
            kb.button(text="Показать результат", callback_data="show_result")
            kb.button(text="Пройти опрос заново", callback_data="restart_survey")
            await message.answer(
                f"{gpt_response}\n\nТеперь вы можете увидеть подобранный дом или начать поиск заново.",
                reply_markup=kb.as_markup()
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
        "подберу дом",
        "анализирую ваши ответы",
        "поиск подходящих вариантов"
    ]
    
    response_lower = response.lower()
    return any(keyword in response_lower for keyword in completion_keywords)


async def send_survey_to_kafka(user_id: int, state: FSMContext, houses: list) -> None:
    """Отправить данные опроса в Kafka"""
    try:
        data = await state.get_data()
        survey_data = {
            "timestamp": data.get("timestamp"),
            "conversation_history": data.get("conversation_history", []),
            "houses": houses
        }
        
        await kafka_service.send_survey_result(user_id, survey_data)
        logger.info(f"Survey data sent to Kafka for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send survey data to Kafka: {e}")


