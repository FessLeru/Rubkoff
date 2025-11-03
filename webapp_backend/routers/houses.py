"""
API routes for houses management
"""
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.db import db
from models.models import House, User, Statistic
from webapp_backend.schemas import (
    HouseSchema, 
    HouseListResponse, 
    HouseDetailResponse, 
    UserRecommendationsResponse,
    UserRecommendationCriteria,
    HouseFilters
)
from core.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/houses", tags=["houses"])


async def get_db_session():
    """Dependency to get database session"""
    async with db.get_db_session() as session:
        yield session


@router.get("/", response_model=HouseListResponse)
async def get_houses(
    min_area: Optional[float] = Query(None, ge=0),
    max_area: Optional[float] = Query(None, ge=0),
    min_floors: Optional[int] = Query(None, ge=1),
    max_floors: Optional[int] = Query(None, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    bedrooms: Optional[int] = Query(None, ge=1),
    bathrooms: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get list of houses with optional filtering
    """
    try:
        # Build query with filters
        query = select(House)
        
        filters_applied = {}
        
        if min_area is not None:
            query = query.where(House.area >= min_area)
            filters_applied["min_area"] = min_area
        if max_area is not None:
            query = query.where(House.area <= max_area)
            filters_applied["max_area"] = max_area
        if min_floors is not None:
            query = query.where(House.floors >= min_floors)
            filters_applied["min_floors"] = min_floors
        if max_floors is not None:
            query = query.where(House.floors <= max_floors)
            filters_applied["max_floors"] = max_floors
        if min_price is not None:
            query = query.where(House.price >= min_price)
            filters_applied["min_price"] = min_price
        if max_price is not None:
            query = query.where(House.price <= max_price)
            filters_applied["max_price"] = max_price
        if bedrooms is not None:
            query = query.where(House.bedrooms == bedrooms)
            filters_applied["bedrooms"] = bedrooms
        if bathrooms is not None:
            query = query.where(House.bathrooms == bathrooms)
            filters_applied["bathrooms"] = bathrooms
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await session.execute(query)
        houses = result.scalars().all()
        
        # Convert to schema
        house_schemas = [HouseSchema.from_orm(house) for house in houses]
        
        # Calculate pagination
        pages = (total + limit - 1) // limit
        
        logger.info(f"Retrieved {len(house_schemas)} houses (page {page}/{pages}, total: {total})")
        
        return HouseListResponse(
            houses=house_schemas,
            total=total,
            page=page,
            pages=pages,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Error retrieving houses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{house_id}", response_model=HouseDetailResponse)
async def get_house_detail(
    house_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information about a specific house
    """
    try:
        # Get house
        result = await session.execute(
            select(House).where(House.id == house_id)
        )
        house = result.scalar_one_or_none()
        
        if not house:
            raise HTTPException(status_code=404, detail="House not found")
        
        # Get similar houses (same floor count or similar area)
        similar_query = select(House).where(
            House.id != house_id
        ).where(
            (House.floors == house.floors) | 
            (House.area.between(house.area * 0.8, house.area * 1.2))
        ).limit(3)
        
        similar_result = await session.execute(similar_query)
        similar_houses = similar_result.scalars().all()
        
        # Convert to schemas
        house_schema = HouseSchema.from_orm(house)
        similar_schemas = [HouseSchema.from_orm(h) for h in similar_houses]
        
        # Gallery with house image
        gallery = [house.image_url] if house.image_url else []
        
        logger.info(f"Retrieved house {house_id} details with {len(similar_schemas)} similar houses")
        
        return HouseDetailResponse(
            house=house_schema,
            similar_houses=similar_schemas,
            gallery=gallery
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving house {house_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{house_id}/view")
async def log_house_view(
    house_id: int,
    user_id: int = Query(..., description="Telegram user ID"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Log that user viewed a house (for analytics)
    """
    try:
        # Check if house exists
        result = await session.execute(
            select(House).where(House.id == house_id)
        )
        house = result.scalar_one_or_none()
        
        if not house:
            raise HTTPException(status_code=404, detail="House not found")
        
        # Check if user exists
        user_result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log view
        stat = Statistic(
            user_id=user_id,
            action="house_view",
            house_id=house_id
        )
        session.add(stat)
        await session.commit()
        
        logger.info(f"Logged house view: user {user_id} viewed house {house_id}")
        
        return {"success": True, "message": "House view logged"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging house view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") 