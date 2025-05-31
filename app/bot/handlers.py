from typing import Optional, Dict, Any
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scraper import get_all_houses
from app.services.gpt_service import chat_with_gpt, find_best_house
from app.bot.keyboards import get_start_keyboard, get_main_keyboard, get_help_keyboard
from app.bot.states import SurveyStates
from app.utils.helpers import log_user_action, notify_house_selection, is_admin
from app.core.config import config

logger = logging.getLogger(__name__)

# Create router
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Handle /start command"""
    try:
        user_id = message.from_user.id if message.from_user else None
        logger.info(f"Processing /start command for user {user_id}")
        
        if not message.from_user:
            logger.warning("No user information in message")
            await message.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        await log_user_action(message.from_user.id, "start", session=session)
        user_is_admin = await is_admin(message.from_user.id, session)
        logger.debug(f"User {message.from_user.id} is_admin: {user_is_admin}")

        await state.set_state(SurveyStates.waiting_for_start)
        
        keyboard = get_main_keyboard(user_is_admin)
        
        text = ("Добро пожаловать, администратор! 👋\n\n"
                "Воспользуйтесь кнопкой ниже для доступа к панели администратора.") if user_is_admin else (
                "Добро пожаловать! 👋\n\n"
                "Я — ваш персональный помощник по подбору идеального дома от компании Rubkoff.\n\n"
                "Я задам вам несколько вопросов о ваших предпочтениях и подберу дом, "
                "который идеально подойдет именно вам.\n\n"
                "Нажмите на кнопку ниже, чтобы начать.")

        await message.answer(text, reply_markup=keyboard)
        logger.info(f"Sent {'admin' if user_is_admin else 'regular'} welcome message to user {message.from_user.id}")
    
    except Exception as e:
        logger.error(f"Error in cmd_start for user {message.from_user.id if message.from_user else 'unknown'}: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при обработке команды. "
            "Пожалуйста, попробуйте позже или обратитесь к администратору @admin"
        )

@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    """Handle /help command"""
    try:
        user_id = message.from_user.id if message.from_user else None
        logger.info(f"Processing /help command for user {user_id}")
        
        if not message.from_user:
            logger.warning("No user information in message")
            await message.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        await log_user_action(message.from_user.id, "help", session=session)
        user_is_admin = await is_admin(message.from_user.id, session)
        logger.debug(f"User {message.from_user.id} is_admin: {user_is_admin}")

        help_text = (
            "📚 <b>Как пользоваться ботом:</b>\n\n"
            "1️⃣ Нажмите кнопку \"Подобрать дом 🏠\" или введите /start для начала диалога\n\n"
            "2️⃣ Я задам вам несколько вопросов о ваших предпочтениях:\n"
            "   • Бюджет\n"
            "   • Желаемая площадь дома\n"
            "   • Количество этажей\n"
            "   • Особенности и пожелания\n\n"
            "3️⃣ После ответа на все вопросы вы получите кнопку \"Показать результат\"\n\n"
            "4️⃣ Я подберу для вас идеальный дом из нашего каталога\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "/start — Начать диалог с ботом\n"
            "/help — Показать эту справку\n\n"
            "🏢 <b>О компании Rubkoff:</b>\n"
            "Rubkoff — лидер на рынке частного домостроения. "
            "Мы строим качественные, современные и экологичные дома с 2005 года.\n\n"
            "Посетите наш сайт: https://rubkoff.ru"
        )

        keyboard = get_help_keyboard(user_is_admin)
        await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"Sent help message to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in cmd_help for user {message.from_user.id if message.from_user else 'unknown'}: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при обработке команды. "
            "Пожалуйста, попробуйте позже или обратитесь к администратору @admin"
        )

@router.callback_query(F.data == "help")
async def help_button(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle help button click"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        await log_user_action(callback.from_user.id, "help_button", session=session)
        user_is_admin = await is_admin(callback.from_user.id, session)
        
        await cmd_help(callback.message, session)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in help_button: {e}", exc_info=True)
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Start house selection survey"""
    try:
        if callback.from_user:
            await log_user_action(callback.from_user.id, "survey_start", session=session)

        await state.set_state(SurveyStates.in_progress)
        
        houses = await get_all_houses(session)
        if not houses:
            await callback.message.answer("К сожалению, каталог домов пуст. Попробуйте позже.")
            await callback.answer()
            return

        system_message = {
            "role": "system",
            "content": "Начни опрос клиента для подбора дома сразу с первого вопроса про бюджет. "
                      "Используй формат (1/8). Не спрашивай разрешения начать опрос и не добавляй лишнего текста."
        }

        conversation_history = [system_message]
        await state.update_data(conversation_history=conversation_history)

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
        await log_user_action(callback.from_user.id, "survey_restart", session=session)
    
    await state.set_state(SurveyStates.waiting_for_start)
    await cmd_start(callback.message, state, session)
    await callback.answer()

@router.callback_query(F.data == "show_result")
async def show_result(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Show recommended house"""
    try:
        if callback.from_user:
            await log_user_action(callback.from_user.id, "show_result", session=session)

        data = await state.get_data()
        conversation_history = data.get("conversation_history", [])
        houses = await get_all_houses(session)

        if not houses:
            await callback.message.answer("К сожалению, каталог домов пуст. Попробуйте позже.")
            await callback.answer()
            return

        await callback.message.answer("🔍 Анализирую ваши ответы и подбираю идеальный дом...")

        house_id = await find_best_house(conversation_history, houses)
        house = next((h for h in houses if h["id"] == house_id), None)

        if not house:
            await callback.message.answer("К сожалению, подходящий дом не найден. Попробуйте изменить критерии поиска.")
            await callback.answer()
            return

        message = format_house_message(house)
        
        if callback.from_user:
            await log_user_action(
                callback.from_user.id,
                "house_selected",
                house_id=house_id,
                session=session
            )
            await notify_house_selection(
                bot=callback.bot,
                user=callback.from_user,
                house=house,
                session=session
            )

        kb = InlineKeyboardBuilder()
        kb.button(text="Пройти опрос заново", callback_data="restart_survey")

        await callback.message.answer(message, reply_markup=kb.as_markup())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_result: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await callback.answer()

@router.message(SurveyStates.in_progress)
async def process_survey_step(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process user responses during survey"""
    try:
        if message.from_user:
            await log_user_action(message.from_user.id, "survey_response", session=session)

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

def format_house_message(house: Dict[str, Any]) -> str:
    """Format house information message"""
    message = f"🎉 Ваш идеальный дом:\n\n"
    message += f"🏠 {house['name']}\n"
    message += f"💰 Цена: {house['price']:,.0f} ₽\n".replace(",", " ")
    message += f"📐 Площадь: {house['area']} м²\n"

    if house['bedrooms']:
        message += f"🛏️ Спален: {house['bedrooms']}\n"
    if house['bathrooms']:
        message += f"🚿 Санузлов: {house['bathrooms']}\n"
    if house['floors']:
        message += f"⬆️ Этажей: {house['floors']}\n"

    message += f"\n🌐 Подробнее: {house['url']}"
    message += f"\n\n✅ ID дома: {house['id']}"
    
    return message

def is_survey_complete(response: str) -> bool:
    """Check if survey is complete based on GPT response"""
    completion_phrases = {
        "достаточно информации",
        "могу подобрать",
        "готов показать",
        "подобрать для вас",
        "нашел для вас",
        "покажу результат",
        "достаточно данных",
        "могу предложить",
        "подходящий вариант"
    }
    return any(phrase in response.lower() for phrase in completion_phrases) 