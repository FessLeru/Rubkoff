"""
Роутер для обработки команд /start и /help
"""

from typing import Optional
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import get_main_keyboard, get_help_keyboard
from bot.states import SurveyStates
from utils.helpers import log_user_action, is_admin, register_or_update_user
from core.config import config

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

        # Automatically register or update user in database
        user = await register_or_update_user(message.from_user, session)
        if not user:
            logger.error(f"Failed to register/update user {message.from_user.id}")
            await message.answer("Произошла ошибка при регистрации. Попробуйте позже.")
            return

        await log_user_action(message.from_user.id, "start", session=session)
        user_is_admin = await is_admin(message.from_user.id, session)
        logger.debug(f"User {message.from_user.id} is_admin: {user_is_admin}")

        await state.set_state(SurveyStates.waiting_for_start)
        
        keyboard = get_main_keyboard(user_is_admin)
        
        text = (f"Добро пожаловать, администратор! 👋\n\n"
                "Воспользуйтесь кнопкой ниже для доступа к панели администратора.") if user_is_admin else (
                f"Добро пожаловать! 👋\n\n"
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

        # Auto-register user if not exists
        await register_or_update_user(message.from_user, session)
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
            f"Посетите наш сайт: {config.COMPANY_WEBSITE}"
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

        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "help_button", session=session)
        user_is_admin = await is_admin(callback.from_user.id, session)
        
        await cmd_help(callback.message, session)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in help_button: {e}", exc_info=True)
        await callback.answer("Произошла ошибка")
