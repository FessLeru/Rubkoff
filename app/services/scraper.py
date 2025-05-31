from typing import List, Dict, Any, Optional
import logging
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import re

from app.models.models import House
from app.core.config import config

logger = logging.getLogger(__name__)

class HouseScraper:
    """Service for scraping houses from Rubkoff website"""
    def __init__(self, session: AsyncSession):
        self.session = session
        self.url = config.RUBKOFF_WORKS_URL

    async def _make_request(self) -> Optional[str]:
        """Make HTTP request to the website"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url)
                response.raise_for_status()
                logger.info(f"HTTP Request: {response.status_code} {response.reason_phrase}")
                return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            return None
        except Exception as e:
            logger.error(f"Error making request: {e}")
            return None

    def _parse_house_data(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse single house card data"""
        try:
            # Extract house name
            name_elem = card.select_one('.product-card__title .h3')
            if not name_elem:
                return None
            name = name_elem.text.strip()

            # Extract area
            area = self._extract_area(card)
            if area is None:
                area = 0

            # Extract dimensions
            dimensions = self._extract_dimensions(card)

            # Extract floors
            floors = self._extract_floors(card)

            # Extract URL
            url = self._extract_url(card)
            if not url:
                return None

            # Extract image URL
            image_url = self._extract_image_url(card)

            # Extract badges
            badges = self._extract_badges(card)

            # Create description
            description = self._create_description(dimensions, badges)

            return {
                "name": name,
                "price": 0,  # Price not available on the website
                "area": area,
                "bedrooms": None,  # Not available on the website
                "bathrooms": None,  # Not available on the website
                "floors": floors,
                "description": description,
                "url": url,
                "image_url": image_url
            }
        except Exception as e:
            logger.error(f"Error parsing house card: {e}")
            return None

    def _extract_area(self, card: BeautifulSoup) -> Optional[float]:
        """Extract area from house card"""
        try:
            area_elem = card.select_one('.product-card__char:has(.h6:contains("Площадь:"))')
            if area_elem:
                area_text = area_elem.select_one('.h6:not(._key)').text.strip()
                area_match = re.search(r'(\d+[.,]?\d*)', area_text)
                if area_match:
                    return float(area_match.group(1).replace(',', '.'))
        except Exception as e:
            logger.error(f"Error extracting area: {e}")
        return None

    def _extract_dimensions(self, card: BeautifulSoup) -> Optional[str]:
        """Extract dimensions from house card"""
        try:
            dimensions_elem = card.select_one('.product-card__char:has(.h6:contains("Размер:"))')
            if dimensions_elem:
                return dimensions_elem.select_one('.h6:not(._key)').text.strip()
        except Exception as e:
            logger.error(f"Error extracting dimensions: {e}")
        return None

    def _extract_floors(self, card: BeautifulSoup) -> Optional[float]:
        """Extract number of floors from house card"""
        try:
            floors_elem = card.select_one('.product-card__char:has(.h6:contains("Этажность:"))')
            if floors_elem:
                floors_text = floors_elem.select_one('.h6:not(._key)').text.strip()
                if "1 этаж + мансарда" in floors_text:
                    return 1.5
                floors_match = re.search(r'(\d+)', floors_text)
                if floors_match:
                    return int(floors_match.group(1))
        except Exception as e:
            logger.error(f"Error extracting floors: {e}")
        return None

    def _extract_url(self, card: BeautifulSoup) -> Optional[str]:
        """Extract URL from house card"""
        try:
            url = card.get('href')
            if url:
                if not url.startswith('http'):
                    url = f"{config.COMPANY_WEBSITE}{url}"
                return url
        except Exception as e:
            logger.error(f"Error extracting URL: {e}")
        return None

    def _extract_image_url(self, card: BeautifulSoup) -> Optional[str]:
        """Extract image URL from house card"""
        try:
            img_elem = card.select_one('.card-gallery__slide img')
            if img_elem:
                image_url = img_elem.get('data-src') or img_elem.get('src')
                if image_url and not image_url.startswith('http'):
                    return f"{config.COMPANY_WEBSITE}{image_url}"
                return image_url
        except Exception as e:
            logger.error(f"Error extracting image URL: {e}")
        return None

    def _extract_badges(self, card: BeautifulSoup) -> List[str]:
        """Extract badges from house card"""
        try:
            return [badge.text.strip() for badge in card.select('.badge') if badge.text.strip()]
        except Exception as e:
            logger.error(f"Error extracting badges: {e}")
        return []

    def _create_description(self, dimensions: Optional[str], badges: List[str]) -> str:
        """Create description from available data"""
        description_parts = []
        if dimensions and dimensions != "x м":
            description_parts.append(f"Размер: {dimensions}")
        if badges:
            description_parts.append(f"Особенности: {', '.join(badges)}")
        return ". ".join(description_parts) if description_parts else None

    async def parse_houses(self) -> int:
        """Parse houses from website and save to database"""
        logger.info(f"Starting house parsing from {self.url}")

        html_content = await self._make_request()
        if not html_content:
            return 0

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            house_cards = soup.select('.gallery-grid .product-card')
            logger.info(f"Found {len(house_cards)} house cards")

            houses = []
            for card in house_cards:
                house_data = self._parse_house_data(card)
                if house_data:
                    house = House(**house_data)
                    houses.append(house)
                    logger.debug(f"Processed house: {house_data['name']}, area: {house_data['area']} м²")

            # Clear existing houses
            await self.session.execute(text("DELETE FROM houses"))

            # Save new houses
            for house in houses:
                self.session.add(house)
            await self.session.commit()

            logger.info(f"Successfully saved {len(houses)} houses to database")
            return len(houses)

        except Exception as e:
            logger.error(f"Error parsing houses: {e}", exc_info=True)
            await self.session.rollback()
            return 0

async def parse_houses(session: AsyncSession) -> int:
    """Wrapper function for backward compatibility"""
    scraper = HouseScraper(session)
    return await scraper.parse_houses()

async def get_all_houses(session: AsyncSession) -> List[Dict[str, Any]]:
    """Get all houses from database"""
    try:
        result = await session.execute(text("SELECT * FROM houses"))
        return [dict(
            id=row[0],
            name=row[1],
            price=row[2],
            area=row[3],
            bedrooms=row[4],
            bathrooms=row[5],
            floors=row[6],
            description=row[7],
            url=row[8],
            image_url=row[9]
        ) for row in result]
    except Exception as e:
        logger.error(f"Error getting houses from database: {e}")
        return [] 