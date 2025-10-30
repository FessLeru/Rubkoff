"""
API routes for user management and recommendations
"""
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.db import db
from models.models import User, House, Statistic
from schemas import (
    UserRecommendationsResponse,
    UserRecommendationCriteria,
    HouseSchema,
    UserStatsResponse
)
from services.recommendation_service import recommendation_service
from core.config import config

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
        # Check if user exists, create if not
        user_result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # Auto-create user for seamless frontend experience
            user = User(
                user_id=user_id,
                first_name="Unknown",
                username=f"user_{user_id}",
                registered_at=datetime.now(),
                last_activity=datetime.now()
            )
            session.add(user)
            await session.commit()
            logger.info(f"Auto-created user {user_id} for recommendations")
        
        # Get real recommendations from database
        has_recommendations = await recommendation_service.has_recommendations(user_id, session)
        
        if has_recommendations:
            # Get saved recommendations from database
            saved_recommendations = await recommendation_service.get_user_recommendations(
                user_id, session, limit=3
            )
            
            if saved_recommendations:
                recommendations = [HouseSchema(**house) for house in saved_recommendations]
                
                # Get user criteria from database
                user_criteria = await recommendation_service.get_user_criteria(user_id, session)
                
                # Create criteria response
                criteria = UserRecommendationCriteria()
                if user_criteria:
                    criteria.min_area = user_criteria.get('min_area')
                    criteria.max_area = user_criteria.get('max_area')
                    criteria.min_floors = user_criteria.get('min_floors')
                    criteria.max_floors = user_criteria.get('max_floors')
                    criteria.min_price = user_criteria.get('min_price')
                    criteria.max_price = user_criteria.get('max_price')
                    criteria.bedrooms = user_criteria.get('bedrooms')
                    criteria.bathrooms = user_criteria.get('bathrooms')
                
                return UserRecommendationsResponse(
                    recommendations=recommendations,
                    criteria=criteria,
                    generated_at=saved_recommendations[0].get('generated_at', datetime.now()),
                    total_matches=len(recommendations)
                )
        
        # Fallback to default service if no recommendations found
        houses = await recommendation_service.get_recommendations_for_user(user_id, session, limit=3)
        recommendations = [HouseSchema(**house) for house in houses]
        
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