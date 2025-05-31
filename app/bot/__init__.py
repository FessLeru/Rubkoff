"""
Bot module
Contains handlers, keyboards, states and middlewares for the Telegram bot
"""

from .handlers import router as main_router
from .admin_handlers import router as admin_router
from .middlewares import DatabaseMiddleware
from .states import UserState
from .keyboards import get_main_keyboard, get_admin_panel_keyboard 