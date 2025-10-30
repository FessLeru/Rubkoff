"""
Пользовательские хендлеры для взаимодействия с ботом
"""

from .start_router import router as start_router
from .survey_router import router as survey_router
from .results_router import router as results_router

__all__ = [
    'start_router',
    'survey_router',
    'results_router'
]
