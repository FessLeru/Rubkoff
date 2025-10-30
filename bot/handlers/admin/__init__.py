"""
Админские хендлеры для управления ботом
"""

from .admin_panel_router import router as admin_panel_router
from .admin_stats_router import router as admin_stats_router
from .admin_broadcast_router import router as admin_broadcast_router
from .admin_catalog_router import router as admin_catalog_router

__all__ = [
    'admin_panel_router',
    'admin_stats_router', 
    'admin_broadcast_router',
    'admin_catalog_router'
]
