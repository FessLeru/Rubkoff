"""
Services module
Contains GPT integration, house scraping services, and mock services
"""

from .gpt_service import GPTService
from .scraper import HouseScraper, parse_houses, get_all_houses
from .mock_service import MockHouseSelectionService, mock_service 