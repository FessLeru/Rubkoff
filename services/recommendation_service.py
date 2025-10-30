"""
Service for managing user recommendations
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from models.models import UserRecommendation, House, User
from core.config import config

logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for managing user recommendations"""
    
    def __init__(self):
        logger.info("RecommendationService initialized")
    
    async def save_recommendations(
        self,
        user_id: int,
        house_ids: List[int],
        criteria: Optional[Dict[str, Any]] = None,
        scores: Optional[List[int]] = None,
        reasons: Optional[List[List[str]]] = None,
        session: AsyncSession = None
    ) -> bool:
        """
        Save user recommendations to database
        
        Args:
            user_id: Telegram user ID
            house_ids: List of house IDs to recommend
            criteria: User criteria used for recommendation
            scores: List of recommendation scores for each house
            reasons: List of match reasons for each house
            session: Database session
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not session:
            logger.error("No database session provided")
            return False
            
        try:
            # Clear existing recommendations for this user
            await session.execute(
                delete(UserRecommendation).where(UserRecommendation.user_id == user_id)
            )
            
            # Save new recommendations
            for i, house_id in enumerate(house_ids):
                score = scores[i] if scores and i < len(scores) else 85
                house_reasons = reasons[i] if reasons and i < len(reasons) else []
                
                recommendation = UserRecommendation(
                    user_id=user_id,
                    house_id=house_id,
                    recommendation_score=score,
                    match_reasons=json.dumps(house_reasons, ensure_ascii=False),
                    criteria=json.dumps(criteria, ensure_ascii=False) if criteria else None,
                    is_primary=(i == 0)  # First house is primary
                )
                session.add(recommendation)
            
            await session.commit()
            logger.info(f"Saved {len(house_ids)} recommendations for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving recommendations for user {user_id}: {e}", exc_info=True)
            await session.rollback()
            return False
    
    async def get_user_recommendations(
        self,
        user_id: int,
        session: AsyncSession = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations for a user
        
        Args:
            user_id: Telegram user ID
            session: Database session
            limit: Maximum number of recommendations to return
            
        Returns:
            List of house recommendations with scores and reasons
        """
        if not session:
            logger.error("No database session provided")
            return []
            
        try:
            # Get user recommendations with house details
            result = await session.execute(
                select(UserRecommendation, House)
                .join(House, UserRecommendation.house_id == House.id)
                .where(UserRecommendation.user_id == user_id)
                .order_by(UserRecommendation.recommendation_score.desc())
                .limit(limit)
            )
            
            recommendations = []
            for rec, house in result.all():
                # Parse JSON fields
                try:
                    match_reasons = json.loads(rec.match_reasons) if rec.match_reasons else []
                    criteria = json.loads(rec.criteria) if rec.criteria else {}
                except (json.JSONDecodeError, TypeError):
                    match_reasons = []
                    criteria = {}
                
                # Build house data
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
                    "created_at": house.created_at,
                    "updated_at": house.updated_at,
                    "recommendation_score": rec.recommendation_score,
                    "match_reasons": match_reasons,
                    "criteria": criteria,
                    "generated_at": rec.generated_at
                }
                
                recommendations.append(house_data)
            
            logger.info(f"Retrieved {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}", exc_info=True)
            return []
    
    async def has_recommendations(self, user_id: int, session: AsyncSession = None) -> bool:
        """
        Check if user has any recommendations
        
        Args:
            user_id: Telegram user ID
            session: Database session
            
        Returns:
            bool: True if user has recommendations, False otherwise
        """
        if not session:
            return False
            
        try:
            result = await session.execute(
                select(func.count(UserRecommendation.id))
                .where(UserRecommendation.user_id == user_id)
            )
            count = result.scalar() or 0
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking recommendations for user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_user_criteria(
        self,
        user_id: int,
        session: AsyncSession = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user recommendation criteria
        
        Args:
            user_id: Telegram user ID
            session: Database session
            
        Returns:
            Dict with user criteria or None if not found
        """
        if not session:
            return None
            
        try:
            result = await session.execute(
                select(UserRecommendation.criteria)
                .where(UserRecommendation.user_id == user_id)
                .where(UserRecommendation.is_primary == True)
            )
            criteria_json = result.scalar_one_or_none()
            
            if criteria_json:
                return json.loads(criteria_json)
            return None
            
        except Exception as e:
            logger.error(f"Error getting criteria for user {user_id}: {e}", exc_info=True)
            return None
    
    async def cleanup_old_recommendations(
        self,
        days_old: int = 30,
        session: AsyncSession = None
    ) -> int:
        """
        Cleanup old recommendations
        
        Args:
            days_old: Remove recommendations older than this many days
            session: Database session
            
        Returns:
            Number of removed recommendations
        """
        if not session:
            return 0
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await session.execute(
                delete(UserRecommendation)
                .where(UserRecommendation.generated_at < cutoff_date)
            )
            
            await session.commit()
            removed_count = result.rowcount
            
            logger.info(f"Cleaned up {removed_count} old recommendations")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old recommendations: {e}", exc_info=True)
            await session.rollback()
            return 0

# Global instance
recommendation_service = RecommendationService() 