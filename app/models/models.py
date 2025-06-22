from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates

Base = declarative_base()

class House(Base):
    """Model for houses from Rubkoff website"""
    __tablename__ = "houses"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    area = Column(Float, nullable=False)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    floors = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(255), nullable=False)
    image_url = Column(String(255), nullable=True)
    
    # Additional fields based on page.html structure
    house_size = Column(String(50), nullable=True)  # размер дома (например "20,2x13,5 м")
    badges = Column(String(255), nullable=True)     # бейджи (например "Вживую", "Видео обзор")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @validates('price', 'area')
    def validate_positive(self, key: str, value: float) -> float:
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    @validates('bedrooms', 'bathrooms', 'floors')
    def validate_rooms(self, key: str, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

class User(Base):
    """Model for Telegram bot users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, unique=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    language_code = Column(String(10), nullable=True)
    is_blocked = Column(Boolean, default=False)
    
    @validates('user_id')
    def validate_user_id(self, key: str, value: int) -> int:
        if value <= 0:
            raise ValueError("user_id must be positive")
        return value

class Admin(Base):
    """Model for bot administrators"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, unique=True)
    added_at = Column(DateTime, default=datetime.utcnow)

class Statistic(Base):
    """Model for usage statistics"""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    action = Column(String(50), nullable=False)
    house_id = Column(Integer, ForeignKey("houses.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    @validates('action')
    def validate_action(self, key: str, value: str) -> str:
        allowed_actions = {
            'registered', 'start', 'help', 'survey_start',
            'survey_response', 'house_selected', 'survey_restart',
            'show_result', 'admin_action'
        }
        if value not in allowed_actions:
            raise ValueError(f"Invalid action: {value}")
        return value 