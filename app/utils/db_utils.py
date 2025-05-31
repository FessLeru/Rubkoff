from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, House, Statistic

async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by Telegram ID"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None
) -> User:
    """Create new user"""
    user = User(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code
    )
    session.add(user)
    await session.commit()
    return user

async def update_user_activity(session: AsyncSession, user_id: int) -> None:
    """Update user's last activity timestamp"""
    user = await get_user_by_id(session, user_id)
    if user:
        user.last_activity = datetime.utcnow()
        await session.commit()

async def get_house_by_id(session: AsyncSession, house_id: int) -> Optional[House]:
    """Get house by ID"""
    result = await session.execute(select(House).where(House.id == house_id))
    return result.scalar_one_or_none()

async def get_houses_by_params(
    session: AsyncSession,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_floors: Optional[int] = None,
    max_floors: Optional[int] = None
) -> List[House]:
    """Get houses filtered by parameters"""
    query = select(House)
    
    if min_area is not None:
        query = query.where(House.area >= min_area)
    if max_area is not None:
        query = query.where(House.area <= max_area)
    if min_floors is not None:
        query = query.where(House.floors >= min_floors)
    if max_floors is not None:
        query = query.where(House.floors <= max_floors)
        
    result = await session.execute(query)
    return list(result.scalars().all())

async def add_statistic(
    session: AsyncSession,
    user_id: int,
    action: str,
    house_id: Optional[int] = None
) -> Statistic:
    """Add new statistic record"""
    stat = Statistic(
        user_id=user_id,
        action=action,
        house_id=house_id
    )
    session.add(stat)
    await session.commit()
    return stat

async def get_statistics(session: AsyncSession) -> Dict[str, Any]:
    """Get general statistics"""
    # Total users
    total_users = await session.scalar(select(func.count(User.id)))
    
    # Active users (last 24 hours)
    active_users = await session.scalar(
        select(func.count(User.id))
        .where(User.last_activity >= datetime.utcnow().replace(hour=0, minute=0))
    )
    
    # Total houses
    total_houses = await session.scalar(select(func.count(House.id)))
    
    # Most viewed houses
    most_viewed = await session.execute(
        select(House.id, House.name, func.count(Statistic.id).label('views'))
        .join(Statistic, Statistic.house_id == House.id)
        .group_by(House.id)
        .order_by(func.count(Statistic.id).desc())
        .limit(5)
    )
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_houses": total_houses,
        "most_viewed_houses": [
            {"id": id, "name": name, "views": views}
            for id, name, views in most_viewed
        ]
    } 