"""
Mock service for testing house selection without GPT integration
Uses real houses from database instead of predefined data
"""
import random
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import House

logger = logging.getLogger(__name__)

class MockHouseSelectionService:
    """Mock service for house selection without GPT - uses real database houses"""
    
    def __init__(self):
        logger.info("MockHouseSelectionService initialized - using real database houses")
    
    async def get_random_house_from_db(self, session: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get random house from database"""
        try:
            # Get all houses from database
            result = await session.execute(select(House))
            houses = result.scalars().all()
            
            if not houses:
                logger.warning("No houses found in database for mock selection")
                return None
            
            # Select random house
            selected_house = random.choice(houses)
            
            # Convert to dict format
            house_data = {
                "id": selected_house.id,
                "name": selected_house.name,
                "price": selected_house.price,
                "area": selected_house.area,
                "bedrooms": selected_house.bedrooms,
                "bathrooms": selected_house.bathrooms,
                "floors": selected_house.floors,
                "description": selected_house.description,
                "url": selected_house.url,
                "image_url": selected_house.image_url,
                "house_size": selected_house.house_size,
                "badges": selected_house.badges,
                "created_at": selected_house.created_at.isoformat() if selected_house.created_at else None,
                "updated_at": selected_house.updated_at.isoformat() if selected_house.updated_at else None
            }
            
            logger.info(f"Mock service selected house: {selected_house.name} (ID: {selected_house.id})")
            return house_data
            
        except Exception as e:
            logger.error(f"Error getting random house from database: {e}", exc_info=True)
            return None
    
    async def get_mock_houses_for_mini_app(self, user_id: int, session: AsyncSession, limit: int = 3) -> List[Dict[str, Any]]:
        """Get multiple random houses for mini-app with recommendation scores"""
        try:
            # Get all houses from database
            result = await session.execute(select(House))
            houses = result.scalars().all()
            
            if not houses:
                logger.warning("No houses found in database for mock mini-app")
                return []
            
            # Select random houses (up to limit)
            selected_houses = random.sample(houses, min(len(houses), limit))
            
            mock_houses = []
            for i, house in enumerate(selected_houses):
                # Generate random recommendation score and reasons for display
                score = random.randint(85, 98)
                reasons = self._generate_mock_reasons()
                
                house_data = {
                    "id": house.id,
                    "name": house.name,
                    "price": house.price,
                    "area": house.area,
                    "bedrooms": house.bedrooms,
                    "bathrooms": house.bathrooms,
                    "floors": house.floors,
                    "description": house.description,
                    "url": house.url,
                    "image_url": house.image_url,
                    "house_size": house.house_size,
                    "badges": house.badges,
                    "recommendation_score": score,
                    "match_reasons": reasons[:random.randint(2, 4)]  # Random 2-4 reasons
                }
                
                mock_houses.append(house_data)
            
            # Sort by recommendation score descending
            mock_houses.sort(key=lambda x: x["recommendation_score"], reverse=True)
            
            logger.info(f"Mock service generated {len(mock_houses)} houses for mini-app (user: {user_id})")
            return mock_houses
            
        except Exception as e:
            logger.error(f"Error generating mock houses for mini-app: {e}", exc_info=True)
            return []
    
    def _generate_mock_reasons(self) -> List[str]:
        """Generate mock match reasons for display"""
        reasons_pool = [
            "Соответствует вашим предпочтениям по площади",
            "Оптимальное соотношение цена-качество",
            "Подходящее количество комнат",
            "Удачная планировка дома",
            "Качественные материалы строительства",
            "Современный архитектурный стиль",
            "Хорошее расположение участка",
            "Энергоэффективные решения",
            "Продуманная планировка участка",
            "Высокое качество отделки",
            "Надежная конструкция дома",
            "Экологичные материалы",
            "Функциональная планировка",
            "Привлекательный внешний вид"
        ]
        
        return random.sample(reasons_pool, len(reasons_pool))
    
    async def process_mock_selection(self, user_id: int, session: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Process house selection in mock mode
        Returns a random house from database with mock enhancement
        """
        try:
            house_data = await self.get_random_house_from_db(session)
            
            if not house_data:
                return None
            
            # Add mock enhancement fields
            house_data.update({
                "recommendation_score": random.randint(90, 98),
                "match_reasons": self._generate_mock_reasons()[:3],  # 3 random reasons
                "selection_method": "mock_random",
                "user_id": user_id
            })
            
            logger.info(f"Mock selection completed for user {user_id}: house {house_data['name']}")
            return house_data
            
        except Exception as e:
            logger.error(f"Error in mock selection process: {e}", exc_info=True)
            return None
    
    def is_mock_mode(self) -> bool:
        """Check if service is in mock mode (always True for this service)"""
        return True
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "service_type": "mock",
            "data_source": "database",
            "random_selection": True,
            "enhanced_display": True,
            "description": "Mock service using real houses from database with random selection"
        }

# Create global mock service instance
mock_service = MockHouseSelectionService()

# Export functions for compatibility (deprecated - use mock_service directly)
async def mock_chat_with_gpt(user_message: str, conversation_history: List[Dict[str, str]], houses: List[Dict[str, Any]], user_id: int) -> Optional[str]:
    """Mock version of chat_with_gpt - deprecated, not used in new flow"""
    # In new mock mode, we don't use chat - just return house immediately
    return None

async def mock_find_best_house(conversation_history: List[Dict[str, str]], houses: List[Dict[str, Any]], user_id: int, session: AsyncSession) -> Optional[int]:
    """Mock version of find_best_house"""
    house = await mock_service.get_mock_house_recommendation(user_id, session)
    return house["id"] if house else None 