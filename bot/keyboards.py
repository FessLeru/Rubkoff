"""Keyboard layouts for the bot"""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import config
from utils.constants import (
    START_COMMAND, HELP_COMMAND, ADMIN_COMMAND,
    BROADCAST_COMMAND, STATS_COMMAND, UPDATE_CATALOG_COMMAND,
    BUTTON_YES, BUTTON_NO, BUTTON_CANCEL, BUTTON_BACK,
    BUTTON_MORE, BUTTON_RESTART, BUTTON_WEBSITE
)

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Get start keyboard for regular users"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Подобрать дом 🏠", callback_data="start_survey")
    kb.button(text="Помощь ❓", callback_data="help")
    kb.adjust(1)
    return kb.as_markup()

def get_help_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Get help keyboard"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Подобрать дом 🏠", callback_data="start_survey")
    if is_admin:
        kb.button(text="Панель администратора 🔧", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Get main keyboard with basic commands"""
    kb = InlineKeyboardBuilder()
    kb.button(text=START_COMMAND, callback_data="start_survey")
    kb.button(text=HELP_COMMAND, callback_data="help")
    
    if is_admin:
        kb.button(text=ADMIN_COMMAND, callback_data="admin_panel")
    
    kb.adjust(2)
    return kb.as_markup()

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for admin panel"""
    kb = InlineKeyboardBuilder()
    kb.button(text=STATS_COMMAND, callback_data="admin:stats")
    kb.button(text=BROADCAST_COMMAND, callback_data="admin:broadcast")
    kb.button(text=UPDATE_CATALOG_COMMAND, callback_data="admin:refresh")
    kb.adjust(2, 1)
    return kb.as_markup()

def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with back to admin panel button"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Вернуться в панель администратора", callback_data="admin:back_to_admin")
    return kb.as_markup()

def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for broadcast confirmation"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="admin:confirm_broadcast")
    kb.button(text="❌ Отменить", callback_data="admin:cancel_broadcast")
    kb.button(text="⬅️ Назад", callback_data="admin:back_to_admin")
    kb.adjust(2, 1)
    return kb.as_markup()

def get_house_keyboard(house_id: int, show_more: bool = True) -> InlineKeyboardMarkup:
    """Get keyboard for house display"""
    kb = InlineKeyboardBuilder()
    
    if show_more:
        kb.button(text=BUTTON_MORE, callback_data=f"house:details:{house_id}")
    
    kb.button(text=BUTTON_WEBSITE, callback_data=f"house:website:{house_id}")
    kb.button(text=BUTTON_RESTART, callback_data="restart_survey")
    kb.adjust(2, 1)
    return kb.as_markup()

def get_simple_house_keyboard() -> InlineKeyboardMarkup:
    """Get simple keyboard for house result - no mini app, just basic options"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Подобрать другой дом 🔄", callback_data="restart_survey")
    kb.adjust(1)
    return kb.as_markup()

def get_house_result_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Get keyboard for house result with mini app and restart options"""
    kb = InlineKeyboardBuilder()
    
    # Mini app button - try to add WebApp if config allows
    try:
        # Create mini app URL with user_id
        mini_app_url = f"{config.effective_mini_app_url}?user_id={user_id}" if user_id else config.effective_mini_app_url
        
        # Only add WebApp if URL is HTTPS (Telegram requirement)
        if mini_app_url.startswith("https://"):
            from aiogram.types import WebAppInfo
            kb.button(
                text="🏠 Открыть мини-приложение", 
                web_app=WebAppInfo(url=mini_app_url)
            )
            kb.button(text="Подобрать другой дом 🔄", callback_data="restart_survey")
        else:
            # Fallback for HTTP URLs - show link instead
            kb.button(text="🏠 Ссылка на приложение", callback_data=f"mini_app_link:{user_id}")
            kb.button(text="Подобрать другой дом 🔄", callback_data="restart_survey")
    except Exception:
        # Fallback to simple buttons if WebApp fails
        kb.button(text="🏠 Ссылка на приложение", callback_data=f"mini_app_link:{user_id}")
        kb.button(text="Подобрать другой дом 🔄", callback_data="restart_survey")
    
    kb.adjust(1)
    return kb.as_markup()

def get_local_test_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for local testing - no WebApp (requires HTTPS)"""
    kb = InlineKeyboardBuilder()
    
    # Simple buttons without WebApp - Telegram requires HTTPS for WebApp
    kb.button(text="Подобрать другой дом 🔄", callback_data="restart_survey")
    kb.button(text="🧪 Локальный тест", callback_data="local_test_info")
    kb.button(text="📊 API тест", callback_data="api_test_info")
    kb.adjust(1)
    return kb.as_markup()

def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Get confirmation keyboard with Yes/No buttons"""
    kb = InlineKeyboardBuilder()
    kb.button(text=BUTTON_YES, callback_data=f"confirm:{action}")
    kb.button(text=BUTTON_NO, callback_data=f"cancel:{action}")
    kb.adjust(2)
    return kb.as_markup()

def get_back_keyboard(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Get keyboard with back button"""
    kb = InlineKeyboardBuilder()
    kb.button(text=BUTTON_BACK, callback_data=callback_data)
    return kb.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with cancel button"""
    kb = InlineKeyboardBuilder()
    kb.button(text=BUTTON_CANCEL, callback_data="cancel")
    return kb.as_markup()

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard with phone number request button"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_houses_list_keyboard(
    houses: List[dict],
    page: int = 0,
    per_page: int = 5
) -> Optional[InlineKeyboardMarkup]:
    """Get keyboard for houses list with pagination"""
    if not houses:
        return None
        
    kb = InlineKeyboardBuilder()
    start = page * per_page
    end = start + per_page
    
    # Add house buttons
    for house in houses[start:end]:
        kb.button(
            text=f"🏠 {house['name']} ({house['area']}м²)",
            callback_data=f"house:select:{house['id']}"
        )
    
    # Add navigation buttons if needed
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"houses:page:{page-1}"
        ))
    if end < len(houses):
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Далее",
            callback_data=f"houses:page:{page+1}"
        ))
    
    if nav_buttons:
        kb.row(*nav_buttons)
    
    # Add restart button
    kb.button(text=BUTTON_RESTART, callback_data="restart_survey")
    
    kb.adjust(1)
    return kb.as_markup() 