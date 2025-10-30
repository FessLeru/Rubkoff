"""
Модуль handlers содержит все роутеры для обработки сообщений бота
"""

from .user import start_router, survey_router, results_router
from .admin import admin_panel_router, admin_stats_router, admin_broadcast_router, admin_catalog_router

# Объединяем все роутеры в один основной роутер
from aiogram import Router

main_router = Router()
admin_router = Router()

# Подключаем пользовательские роутеры к основному
main_router.include_router(start_router)
main_router.include_router(survey_router)
main_router.include_router(results_router)

# Подключаем админские роутеры к админскому
admin_router.include_router(admin_panel_router)
admin_router.include_router(admin_stats_router)
admin_router.include_router(admin_broadcast_router)
admin_router.include_router(admin_catalog_router)

__all__ = [
    'main_router',
    'admin_router',
    'start_router',
    'survey_router', 
    'results_router',
    'admin_panel_router',
    'admin_stats_router',
    'admin_broadcast_router',
    'admin_catalog_router'
]
