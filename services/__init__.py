"""
Services module
Contains GPT integration, house scraping services, and recommendation services
"""

from .gpt_service import GPTService
from .scraper import HouseScraper, parse_houses, get_all_houses
from .recommendation_service import recommendation_service 