"""
Pydantic schemas for API responses
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HouseSchema(BaseModel):
    """House information schema"""
    id: int
    name: str
    price: float
    area: float
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floors: Optional[float] = None
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    house_size: Optional[str] = None  # размер дома (например "20,2x13,5 м")
    badges: Optional[str] = None      # бейджи (например "Вживую", "Видео обзор")
    recommendation_score: Optional[int] = None
    match_reasons: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HouseListResponse(BaseModel):
    """Response for house list endpoint"""
    houses: List[HouseSchema]
    total: int
    page: int = 1
    pages: int = 1
    filters_applied: Dict[str, Any] = {}


class HouseDetailResponse(BaseModel):
    """Response for house detail endpoint"""
    house: HouseSchema
    similar_houses: List[HouseSchema] = []
    gallery: List[str] = []


class UserRecommendationCriteria(BaseModel):
    """User recommendation criteria"""
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    min_floors: Optional[int] = None
    max_floors: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None


class UserRecommendationsResponse(BaseModel):
    """Response for user recommendations endpoint"""
    recommendations: List[HouseSchema]
    criteria: UserRecommendationCriteria
    generated_at: datetime
    total_matches: int


class HouseFilters(BaseModel):
    """House filtering parameters"""
    min_area: Optional[float] = Field(None, ge=0)
    max_area: Optional[float] = Field(None, ge=0)
    min_floors: Optional[int] = Field(None, ge=1)
    max_floors: Optional[int] = Field(None, ge=1)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=1)
    bathrooms: Optional[int] = Field(None, ge=1)
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=50)


class APIResponse(BaseModel):
    """Generic API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class UserStatsResponse(BaseModel):
    """User statistics response"""
    user_id: int
    surveys_completed: int
    houses_viewed: int
    last_activity: Optional[datetime] = None
    registration_date: Optional[datetime] = None


class AdminNotificationRequest(BaseModel):
    """Admin notification request"""
    user_id: int
    house_id: int
    message: str
    notification_type: str = "house_selection" 