from typing import Optional, Dict, Any
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scraper import get_all_houses
from app.services.gpt_service import chat_with_gpt, find_best_house
from app.services.mock_service import mock_service, mock_chat_with_gpt, mock_find_best_house
from app.bot.keyboards import (
    get_start_keyboard, get_help_keyboard, 
    get_main_keyboard, get_house_keyboard,
    get_simple_house_keyboard, get_local_test_keyboard,
    get_house_result_keyboard
)
from app.bot.states import SurveyStates
from app.utils.helpers import log_user_action, notify_house_selection, is_admin, register_or_update_user
from app.core.config import config

logger = logging.getLogger(__name__)

# Create router
router = Router()

def is_local_test() -> bool:
    """Check if running in local test mode"""
    return config.effective_mini_app_url.startswith("http://127.0.0.1")

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
        
        mode_info = " (тестовый режим)" if config.MOCK_MODE else ""
        local_info = " 🧪 ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ" if is_local_test() else ""
        
        text = (f"Добро пожаловать, администратор! 👋{mode_info}{local_info}\n\n"
                "Воспользуйтесь кнопкой ниже для доступа к панели администратора.") if user_is_admin else (
                f"Добро пожаловать! 👋{mode_info}{local_info}\n\n"
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

        mode_info = "\n\n🧪 <b>Внимание:</b> Бот работает в тестовом режиме" if config.MOCK_MODE else ""

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
            f"Посетите наш сайт: {config.COMPANY_WEBSITE}{mode_info}"
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

@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Start the house selection survey"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "survey_start", session=session)

        if config.MOCK_MODE:
            # Mock mode - show result immediately without questions
            logger.info(f"Mock mode - showing result immediately for user {callback.from_user.id}")
            
            await callback.message.answer("🔍 Подбираю дом...")
            
            # Use mock service with database
            house_data = await mock_service.process_mock_selection(callback.from_user.id, session)
            if not house_data:
                await callback.message.answer("К сожалению, подходящий дом не найден. Попробуйте изменить критерии поиска.")
                await callback.answer()
                return

            message = format_mock_house_message(house_data)
            
            # Choose keyboard based on environment
            if is_local_test():
                keyboard = get_local_test_keyboard(callback.from_user.id)
            else:
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
                house=house_data,
                session=session
            )
            
            await state.set_state(SurveyStates.finished)
        else:
            # Production mode - start survey with questions
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
        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "survey_restart", session=session)
    
    await state.set_state(SurveyStates.waiting_for_start)
    await cmd_start(callback.message, state, session)
    await callback.answer()

@router.callback_query(F.data == "api_test_info")
async def api_test_info(callback: CallbackQuery, session: AsyncSession):
    """Show local API test information"""
    try:
        if callback.from_user:
            await register_or_update_user(callback.from_user, session)
            await log_user_action(callback.from_user.id, "api_test_info", session=session)
        
        message = (
            "🧪 <b>Локальное API тестирование</b>\n\n"
            "📱 <b>Мини-приложение:</b>\n"
            "http://127.0.0.1:8000/frontend/?user_id=123\n\n"
            "❤️ <b>API Health:</b>\n"
            "http://127.0.0.1:8000/api/health\n\n"
            "🏠 <b>Mock API домов:</b>\n"
            "http://127.0.0.1:8000/api/houses/mock/recommendations\n\n"
            "📋 <b>API Документация:</b>\n"
            "http://127.0.0.1:8000/docs\n\n"
            "💡 <i>Откройте эти ссылки в браузере для тестирования</i>"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Подобрать другой дом", callback_data="restart_survey")
        kb.adjust(1)
        
        await callback.message.answer(message, reply_markup=kb.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in api_test_info: {e}", exc_info=True)
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data == "local_test_info")
async def local_test_info(callback: CallbackQuery, session: AsyncSession):
    """Show local test mini app information"""
    try:
        if callback.from_user:
            await register_or_update_user(callback.from_user, session)
            await log_user_action(callback.from_user.id, "local_test_info", session=session)
        
        message = (
            "🧪 <b>Локальное тестирование мини-приложения</b>\n\n"
            "📱 <b>Тестовое приложение:</b>\n"
            "http://127.0.0.1:8000/frontend/test-welcome.html\n\n"
            "✨ <b>Что можно протестировать:</b>\n"
            "• Интерфейс мини-приложения\n"
            "• Проверка статуса API\n"
            "• Тест запросов к серверу\n"
            "• Переходы между страницами\n\n"
            "💡 <i>Откройте ссылку в браузере для тестирования интерфейса</i>\n\n"
            "⚠️ <i>Примечание: В Telegram Mini App требует HTTPS, поэтому для локального тестирования используйте браузер</i>"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Подобрать другой дом", callback_data="restart_survey")
        kb.button(text="📊 API тест", callback_data="api_test_info")
        kb.adjust(1)
        
        await callback.message.answer(message, reply_markup=kb.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in local_test_info: {e}", exc_info=True)
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data == "show_result")
async def show_result(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Show recommended house"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        await register_or_update_user(callback.from_user, session)
        await log_user_action(callback.from_user.id, "show_result", session=session)

        await callback.message.answer("🔍 Анализирую ваши ответы и подбираю идеальный дом...")

        if config.MOCK_MODE:
            # Use mock service with database
            house_data = await mock_service.process_mock_selection(callback.from_user.id, session)
            if not house_data:
                await callback.message.answer("К сожалению, подходящий дом не найден. Попробуйте изменить критерии поиска.")
                await callback.answer()
                return

            message = format_mock_house_message(house_data)
            
            # Choose keyboard based on environment
            if is_local_test():
                keyboard = get_local_test_keyboard(callback.from_user.id)
            else:
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
                house=house_data,
                session=session
            )
        else:
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

        await state.set_state(SurveyStates.finished)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in show_result: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await callback.answer()

@router.message(SurveyStates.in_progress)
async def process_survey_step(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process user responses during survey"""
    try:
        if not message.from_user:
            return

        await register_or_update_user(message.from_user, session)
        await log_user_action(message.from_user.id, "survey_response", session=session)

        if config.MOCK_MODE:
            # Use mock service
            response, is_complete = await mock_service.process_mock_response(
                message.from_user.id, 
                message.text
            )
            
            if is_complete:
                await state.set_state(SurveyStates.finished)
                kb = InlineKeyboardBuilder()
                kb.button(text="Показать результат", callback_data="show_result")
                kb.button(text="Пройти опрос заново", callback_data="restart_survey")
                kb.adjust(1)
                await message.answer(
                    f"{response}\n\nТеперь вы можете увидеть подобранный дом или начать поиск заново.",
                    reply_markup=kb.as_markup()
                )
            else:
                await message.answer(response)
        else:
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

def format_mock_house_message(house_data: Dict[str, Any]) -> str:
    """Format mock house message with recommendation score and reasons"""
    message = (
        f"🏠 <b>{house_data['name']}</b>\n\n"
        f"💰 Цена: {house_data['price']:,} ₽\n"
        f"📏 Площадь: {house_data['area']} м²\n"
    )
    
    if house_data.get('bedrooms'):
        message += f"🛏 Спален: {house_data['bedrooms']}\n"
    if house_data.get('bathrooms'):
        message += f"🚿 Санузлов: {house_data['bathrooms']}\n"
    if house_data.get('floors'):
        message += f"🏗 Этажей: {house_data['floors']}\n"
    
    if house_data.get('recommendation_score'):
        message += f"\n🎯 Соответствие: {house_data['recommendation_score']}%\n"
    
    if house_data.get('match_reasons'):
        message += "\n✅ <b>Почему этот дом вам подходит:</b>\n"
        for reason in house_data['match_reasons'][:3]:  # Show first 3 reasons
            message += f"• {reason}\n"
    
    if house_data.get('description'):
        message += f"\n📝 {house_data['description']}\n"
    
    message += f"\n🔗 <a href='{house_data['url']}'>Подробнее на сайте</a>"
    
    return message

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