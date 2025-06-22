"""
API routes for user management and recommendations
"""
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db import db
from app.models.models import User, House, Statistic
from app.api.schemas import (
    UserRecommendationsResponse,
    UserRecommendationCriteria,
    HouseSchema,
    UserStatsResponse
)
from app.services.mock_service import mock_service
from app.core.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user", tags=["users"])


async def get_db_session():
    """Dependency to get database session"""
    async with db.get_db_session() as session:
        yield session


@router.get("/{user_id}/recommendations", response_model=UserRecommendationsResponse)
async def get_user_recommendations(
    user_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get house recommendations for a specific user
    """
    try:
        # Check if user exists
        user_result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if config.MOCK_MODE:
            # Use mock service with real database houses
            houses = await mock_service.get_mock_houses_for_mini_app(user_id, session)
            recommendations = [HouseSchema(**house) for house in houses]
            
            # Mock criteria
            criteria = UserRecommendationCriteria(
                min_area=100.0,
                max_area=200.0,
                min_floors=1,
                max_floors=2
            )
            
            return UserRecommendationsResponse(
                recommendations=recommendations,
                criteria=criteria,
                generated_at=datetime.now(),
                total_matches=len(recommendations)
            )
        else:
            # Get user's survey responses and house selections from statistics
            stats_result = await session.execute(
                select(Statistic).where(
                    Statistic.user_id == user_id,
                    Statistic.action.in_(["house_selected", "survey_response"])
                ).order_by(Statistic.timestamp.desc())
            )
            user_stats = stats_result.scalars().all()
            
            if not user_stats:
                # No data available, return empty recommendations
                return UserRecommendationsResponse(
                    recommendations=[],
                    criteria=UserRecommendationCriteria(),
                    generated_at=datetime.now(),
                    total_matches=0
                )
            
            # Analyze user preferences from statistics
            # This is a simplified implementation
            # In production, this would use more sophisticated ML algorithms
            
            # Get recently selected houses to understand preferences
            selected_houses = [stat.house_id for stat in user_stats if stat.house_id]
            
            if selected_houses:
                # Get characteristics of selected houses
                houses_result = await session.execute(
                    select(House).where(House.id.in_(selected_houses))
                )
                selected_house_objects = houses_result.scalars().all()
                
                if selected_house_objects:
                    # Calculate average preferences
                    avg_area = sum(h.area for h in selected_house_objects) / len(selected_house_objects)
                    avg_floors = sum(h.floors or 1 for h in selected_house_objects) / len(selected_house_objects)
                    
                    # Create criteria based on user preferences
                    criteria = UserRecommendationCriteria(
                        min_area=avg_area * 0.8,
                        max_area=avg_area * 1.2,
                        min_floors=max(1, int(avg_floors - 0.5)),
                        max_floors=int(avg_floors + 0.5)
                    )
                    
                    # Find similar houses
                    similar_query = select(House).where(
                        House.id.notin_(selected_houses),
                        House.area.between(criteria.min_area, criteria.max_area),
                        House.floors.between(criteria.min_floors, criteria.max_floors)
                    ).limit(10)
                    
                    similar_result = await session.execute(similar_query)
                    similar_houses = similar_result.scalars().all()
                    
                    recommendations = [HouseSchema.from_orm(house) for house in similar_houses]
                    
                    # Add recommendation scores (simplified)
                    for i, rec in enumerate(recommendations):
                        rec.recommendation_score = 90 - (i * 5)
                        rec.match_reasons = ["Похожая площадь", "Подходящая этажность"]
                else:
                    criteria = UserRecommendationCriteria()
                    recommendations = []
            else:
                criteria = UserRecommendationCriteria()
                recommendations = []
            
            return UserRecommendationsResponse(
                recommendations=recommendations,
                criteria=criteria,
                generated_at=datetime.now(),
                total_matches=len(recommendations)
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get user statistics
    """
    try:
        # Check if user exists
        user_result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get survey completions
        surveys_completed = await session.scalar(
            select(func.count(Statistic.id)).where(
                Statistic.user_id == user_id,
                Statistic.action == "survey_finished"
            )
        ) or 0
        
        # Get house views
        houses_viewed = await session.scalar(
            select(func.count(Statistic.id)).where(
                Statistic.user_id == user_id,
                Statistic.action.in_(["house_view", "house_selected"])
            )
        ) or 0
        
        return UserStatsResponse(
            user_id=user_id,
            surveys_completed=surveys_completed,
            houses_viewed=houses_viewed,
            last_activity=user.last_activity,
            registration_date=user.registered_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{user_id}/activity")
async def update_user_activity(
    user_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update user's last activity timestamp
    """
    try:
        # Check if user exists
        user_result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update last activity
        user.last_activity = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Updated activity for user {user_id}")
        
        return {"success": True, "message": "Activity updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating activity for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") 