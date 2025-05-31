from typing import Optional, Dict, Any
from app.core.config import config

def format_house_info(house: Dict[str, Any], detailed: bool = False) -> str:
    """Format house information for message"""
    name = house.get('name', 'Без названия')
    area = house.get('area', 0)
    floors = house.get('floors', 'Не указано')
    
    base_info = [
        f"🏠 <b>{name}</b>",
        f"📏 Площадь: {area} {config.AREA_SYMBOL}",
        f"🏗 Этажность: {floors}"
    ]
    
    if detailed:
        if house.get('description'):
            base_info.append(f"\n📝 Описание:\n{house['description']}")
        if house.get('url'):
            base_info.append(f"\n🔗 <a href='{house['url']}'>Подробнее на сайте</a>")
    
    return "\n".join(base_info)

def format_user_info(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> str:
    """Format user information for message"""
    parts = [f"ID: {user_id}"]
    
    if username:
        parts.append(f"Username: @{username}")
    if first_name:
        parts.append(f"Имя: {first_name}")
    if last_name:
        parts.append(f"Фамилия: {last_name}")
        
    return "\n".join(parts)

def format_statistics(stats: Dict[str, Any]) -> str:
    """Format statistics for message"""
    text = [
        "📊 <b>Статистика бота</b>\n",
        f"👥 Всего пользователей: {stats['total_users']}",
        f"👤 Активных за сутки: {stats['active_users']}",
        f"🏠 Всего домов: {stats['total_houses']}"
    ]
    
    if stats['most_viewed_houses']:
        text.append("\n🔍 Самые просматриваемые дома:")
        for house in stats['most_viewed_houses']:
            text.append(
                f"• {house['name']} - {house['views']} просмотров"
            )
    
    return "\n".join(text)

def format_error(error: str) -> str:
    """Format error message"""
    return f"❌ Ошибка: {error}"

def format_success(message: str) -> str:
    """Format success message"""
    return f"✅ {message}"

def format_broadcast_message(message: str, from_user: Dict[str, Any]) -> str:
    """Format broadcast message with sender info"""
    sender_info = format_user_info(
        from_user['id'],
        from_user.get('username'),
        from_user.get('first_name'),
        from_user.get('last_name')
    )
    return (
        f"📢 <b>Сообщение от администратора:</b>\n\n"
        f"{message}\n\n"
        f"<i>Отправитель:\n{sender_info}</i>"
    ) 