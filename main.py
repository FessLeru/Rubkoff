import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from urllib.parse import quote

from config import BOT_TOKEN
from keyboards import get_budget_kb, get_area_kb, get_floors_kb, get_rooms_kb, get_bathrooms_kb, get_material_kb, get_garage_kb, get_style_kb
from ai_handler import get_house_recommendations
from project_matcher import get_recommended_projects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class SurveyStates(StatesGroup):
    budget = State()
    area = State()
    floors = State()
    rooms = State()
    bathrooms = State()
    material = State()
    garage = State()
    style = State()


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я помогу вам подобрать идеальный дом.\n\n"
        "Давайте начнем с нескольких вопросов, чтобы я мог понять ваши предпочтения.",
        reply_markup=None
    )
    await asyncio.sleep(0.5)
    await message.answer(
        "💰 <b>Вопрос 1 из 8</b>\n\n"
        "Какой у вас бюджет на строительство?",
        parse_mode="HTML",
        reply_markup=get_budget_kb()
    )
    await state.set_state(SurveyStates.budget)


@dp.callback_query(SurveyStates.budget, F.data.startswith("budget_"))
async def budget_handler(callback: CallbackQuery, state: FSMContext):
    budget = callback.data.replace("budget_", "")
    
    if budget == "custom":
        await callback.message.edit_text(
            "💰 <b>Вопрос 1 из 8</b>\n\n"
            "Напишите ваш бюджет в миллионах рублей (например: 15)",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(budget=budget)
    await callback.message.edit_text(
        "📐 <b>Вопрос 2 из 8</b>\n\n"
        "Какая площадь дома вам нужна?",
        parse_mode="HTML",
        reply_markup=get_area_kb()
    )
    await state.set_state(SurveyStates.area)
    await callback.answer()


@dp.message(SurveyStates.budget)
async def budget_custom_handler(message: Message, state: FSMContext):
    try:
        budget_value = float(message.text.replace(",", "."))
        await state.update_data(budget=f"{budget_value} млн")
        await message.answer(
            "📐 <b>Вопрос 2 из 8</b>\n\n"
            "Какая площадь дома вам нужна?",
            parse_mode="HTML",
            reply_markup=get_area_kb()
        )
        await state.set_state(SurveyStates.area)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 15)")


@dp.callback_query(SurveyStates.area, F.data.startswith("area_"))
async def area_handler(callback: CallbackQuery, state: FSMContext):
    area = callback.data.replace("area_", "")
    
    if area == "custom":
        await callback.message.edit_text(
            "📐 <b>Вопрос 2 из 8</b>\n\n"
            "Напишите желаемую площадь в м² (например: 200)",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(area=area)
    await callback.message.edit_text(
        "🏠 <b>Вопрос 3 из 8</b>\n\n"
        "Сколько этажей вы хотите?",
        parse_mode="HTML",
        reply_markup=get_floors_kb()
    )
    await state.set_state(SurveyStates.floors)
    await callback.answer()


@dp.message(SurveyStates.area)
async def area_custom_handler(message: Message, state: FSMContext):
    try:
        area_value = int(message.text)
        await state.update_data(area=f"{area_value} м²")
        await message.answer(
            "🏠 <b>Вопрос 3 из 8</b>\n\n"
            "Сколько этажей вы хотите?",
            parse_mode="HTML",
            reply_markup=get_floors_kb()
        )
        await state.set_state(SurveyStates.floors)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 200)")


@dp.callback_query(SurveyStates.floors, F.data.startswith("floors_"))
async def floors_handler(callback: CallbackQuery, state: FSMContext):
    floors = callback.data.replace("floors_", "")
    await state.update_data(floors=floors)
    await callback.message.edit_text(
        "🚪 <b>Вопрос 4 из 8</b>\n\n"
        "Сколько комнат вам нужно?",
        parse_mode="HTML",
        reply_markup=get_rooms_kb()
    )
    await state.set_state(SurveyStates.rooms)
    await callback.answer()


@dp.callback_query(SurveyStates.rooms, F.data.startswith("rooms_"))
async def rooms_handler(callback: CallbackQuery, state: FSMContext):
    rooms = callback.data.replace("rooms_", "")
    
    if rooms == "custom":
        await callback.message.edit_text(
            "🚪 <b>Вопрос 4 из 8</b>\n\n"
            "Напишите количество комнат (например: 5)",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(rooms=rooms)
    await callback.message.edit_text(
        "🚿 <b>Вопрос 5 из 8</b>\n\n"
        "Сколько санузлов вам нужно?",
        parse_mode="HTML",
        reply_markup=get_bathrooms_kb()
    )
    await state.set_state(SurveyStates.bathrooms)
    await callback.answer()


@dp.message(SurveyStates.rooms)
async def rooms_custom_handler(message: Message, state: FSMContext):
    try:
        rooms_value = int(message.text)
        await state.update_data(rooms=f"{rooms_value}")
        await message.answer(
            "🚿 <b>Вопрос 5 из 8</b>\n\n"
            "Сколько санузлов вам нужно?",
            parse_mode="HTML",
            reply_markup=get_bathrooms_kb()
        )
        await state.set_state(SurveyStates.bathrooms)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 5)")


@dp.callback_query(SurveyStates.bathrooms, F.data.startswith("bathrooms_"))
async def bathrooms_handler(callback: CallbackQuery, state: FSMContext):
    bathrooms = callback.data.replace("bathrooms_", "")
    await state.update_data(bathrooms=bathrooms)
    await callback.message.edit_text(
        "🧱 <b>Вопрос 6 из 8</b>\n\n"
        "Из какого материала вы хотите дом?",
        parse_mode="HTML",
        reply_markup=get_material_kb()
    )
    await state.set_state(SurveyStates.material)
    await callback.answer()


@dp.callback_query(SurveyStates.material, F.data.startswith("material_"))
async def material_handler(callback: CallbackQuery, state: FSMContext):
    material = callback.data.replace("material_", "")
    await state.update_data(material=material)
    await callback.message.edit_text(
        "🚗 <b>Вопрос 7 из 8</b>\n\n"
        "Нужен ли вам гараж?",
        parse_mode="HTML",
        reply_markup=get_garage_kb()
    )
    await state.set_state(SurveyStates.garage)
    await callback.answer()


@dp.callback_query(SurveyStates.garage, F.data.startswith("garage_"))
async def garage_handler(callback: CallbackQuery, state: FSMContext):
    garage = callback.data.replace("garage_", "")
    await state.update_data(garage=garage)
    await callback.message.edit_text(
        "🎨 <b>Вопрос 8 из 8</b>\n\n"
        "Какой стиль дома вы предпочитаете?",
        parse_mode="HTML",
        reply_markup=get_style_kb()
    )
    await state.set_state(SurveyStates.style)
    await callback.answer()


@dp.callback_query(SurveyStates.style, F.data.startswith("style_"))
async def style_handler(callback: CallbackQuery, state: FSMContext):
    style = callback.data.replace("style_", "")
    await state.update_data(style=style)
    
    await callback.message.edit_text(
        "⏳ Анализирую ваши предпочтения и подбираю лучшие варианты...",
        parse_mode="HTML"
    )
    await callback.answer()
    
    user_data = await state.get_data()
    
    try:
        recommendations = await get_house_recommendations(user_data)
        
        await callback.message.answer(
            "✨ <b>Вот что я подобрал для вас:</b>\n\n" + recommendations,
            parse_mode="HTML"
        )
        
        await asyncio.sleep(0.5)
        
        # Получаем топ-3 рекомендованных проекта из rubkoff_projects.json на основе предпочтений пользователя
        try:
            recommended_projects = get_recommended_projects(user_data, limit=3)
            
            if not recommended_projects:
                # Если не найдено подходящих, берем первые 3 проекта
                with open("rubkoff_projects.json", "r", encoding="utf-8") as f:
                    all_projects = json.load(f)
                recommended_projects = all_projects[:3] if len(all_projects) >= 3 else all_projects
            
            # Извлекаем URL проектов
            recommended_urls = [project["url"] for project in recommended_projects]
            
            # Формируем URL для мини-приложения
            # ЗАМЕНИТЕ НА ВАШ ХОСТИНГ! Например: https://yourdomain.com/mini_app.html
            MINI_APP_URL = "https://alexanik.ru/Rubkoff/mini_app.html"  # TODO: Замените на ваш URL
            
            # Правильно кодируем JSON массив для URL
            recommended_urls_json = json.dumps(recommended_urls)
            web_app_url = f"{MINI_APP_URL}?house_urls={quote(recommended_urls_json)}"
            
            web_app_button = InlineKeyboardButton(
                text="📱 Посмотреть варианты",
                web_app=WebAppInfo(url=web_app_url)
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
            
            await callback.message.answer(
                "📱 Посмотрите эти варианты с фотографиями:",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка при подготовке мини-приложения: {e}")
            # Если ошибка, просто продолжаем без мини-аппа
        
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        await callback.message.answer(
            "❌ Извините, произошла ошибка при подборе домов. Попробуйте еще раз позже или напишите /start"
        )
    
    await state.clear()


async def main():
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())