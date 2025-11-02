import json
import httpx
from typing import Dict, List, Tuple
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE
from houses_data import get_houses_list


# Коэффициенты для подсчета соответствия
WEIGHTS = {
    'price': 0.25,
    'area': 0.20,
    'floors': 0.10,
    'rooms': 0.15,
    'bathrooms': 0.05,
    'badges': 0.05,  # гараж и др
    'style': 0.10,
    'material': 0.10
}


def parse_price(price_str: str) -> float:
    """Извлекает числовое значение цены в млн"""
    try:
        return float(price_str.split()[0])
    except:
        return 0


def parse_area(area_str: str) -> int:
    """Извлекает площадь в м²"""
    try:
        return int(area_str.split()[0])
    except:
        return 0


def parse_range(value: str) -> Tuple[float, float]:
    """Парсит диапазон типа '10-13' или '300+'"""
    if '+' in value:
        num = float(value.replace('+', '').replace('млн', '').replace('м²', '').strip())
        return (num, num * 2)
    elif '-' in value:
        parts = value.split('-')
        return (float(parts[0]), float(parts[1]))
    else:
        try:
            num = float(value.replace('млн', '').replace('м²', '').strip())
            return (num, num)
        except:
            return (0, 0)


def calculate_price_score(house_price: float, user_budget: str) -> float:
    """Считает соответствие цены (1.0 = идеально, 0.0 = не подходит)"""
    if 'не указан' in user_budget or 'важно' in user_budget:
        return 0.5
    
    min_budget, max_budget = parse_range(user_budget)
    
    if min_budget <= house_price <= max_budget:
        return 1.0
    elif house_price < min_budget:
        diff = (min_budget - house_price) / min_budget
        return max(0.7 - diff, 0)
    else:
        diff = (house_price - max_budget) / max_budget
        return max(0.5 - diff, 0)


def calculate_area_score(house_area: int, user_area: str) -> float:
    """Считает соответствие площади"""
    if 'не указана' in user_area or 'важно' in user_area:
        return 0.5
    
    min_area, max_area = parse_range(user_area)
    
    if min_area <= house_area <= max_area:
        return 1.0
    elif house_area < min_area:
        diff = (min_area - house_area) / min_area
        return max(0.6 - diff, 0)
    else:
        diff = (house_area - max_area) / max_area
        return max(0.7 - diff * 0.5, 0)


def calculate_floors_score(house_floors: str, user_floors: str) -> float:
    """Считает соответствие этажности"""
    if 'важно' in user_floors or 'any' in user_floors:
        return 0.5
    
    user_floors_num = user_floors.replace('этажный', '').strip()
    if user_floors_num == house_floors:
        return 1.0
    else:
        return 0.3


def calculate_rooms_score(house_rooms: str, user_rooms: str) -> float:
    """Считает соответствие количества комнат"""
    if 'важно' in user_rooms:
        return 0.5
    
    try:
        house_rooms_num = int(house_rooms)
        
        if '+' in user_rooms:
            user_min = int(user_rooms.replace('+', ''))
            if house_rooms_num >= user_min:
                return 1.0
            else:
                return max(0.5 - (user_min - house_rooms_num) * 0.2, 0)
        else:
            user_rooms_num = int(user_rooms)
            diff = abs(house_rooms_num - user_rooms_num)
            if diff == 0:
                return 1.0
            elif diff == 1:
                return 0.7
            else:
                return max(0.4 - diff * 0.1, 0)
    except:
        return 0.5


def calculate_bathrooms_score(house_bathrooms: str, user_bathrooms: str) -> float:
    """Считает соответствие количества санузлов"""
    if 'важно' in user_bathrooms or 'any' in user_bathrooms:
        return 0.5
    
    try:
        house_bath_num = int(house_bathrooms)
        
        if '+' in user_bathrooms:
            user_min = int(user_bathrooms.replace('+', ''))
            return 1.0 if house_bath_num >= user_min else 0.6
        else:
            user_bath_num = int(user_bathrooms)
            return 1.0 if house_bath_num >= user_bath_num else 0.7
    except:
        return 0.5


def calculate_garage_score(house_garage: str, user_garage: str) -> float:
    """Считает соответствие наличия гаража"""
    if 'важно' in user_garage or 'any' in user_garage:
        return 0.5
    
    house_has_garage = 'да' in house_garage.lower()
    user_wants_garage = 'yes' in user_garage.lower()
    
    if house_has_garage == user_wants_garage:
        return 1.0
    elif user_wants_garage and not house_has_garage:
        return 0.2
    else:
        return 0.7


def calculate_material_score(house_material: str, user_material: str) -> float:
    """Считает соответствие материала"""
    if 'важно' in user_material or 'any' in user_material:
        return 0.5
    
    material_map = {
        'brick': 'кирпич',
        'wood': 'дерево',
        'gasobeton': 'газобетон',
        'frame': 'каркасный'
    }
    
    user_mat = material_map.get(user_material, user_material).lower()
    house_mat = house_material.lower()
    
    return 1.0 if user_mat in house_mat else 0.3


def calculate_style_score(house_style: str, user_style: str) -> float:
    """Считает соответствие стиля"""
    if 'важно' in user_style or 'any' in user_style:
        return 0.5
    
    style_map = {
        'classic': 'классический',
        'modern': 'современный',
        'chalet': 'шале',
        'american': 'американский',
        'scandinavian': 'скандинавский'
    }
    
    user_st = style_map.get(user_style, user_style).lower()
    house_st = house_style.lower()
    
    return 1.0 if user_st in house_st else 0.4


def calculate_house_score(house: Dict, user_prefs: Dict[str, str]) -> float:
    """Рассчитывает общий балл дома по всем критериям"""
    
    house_price = parse_price(house['price'])
    house_area = parse_area(house['area'])
    
    score = 0.0
    
    # Цена (вес 0.25)
    price_score = calculate_price_score(house_price, user_prefs.get('budget', ''))
    score += price_score * WEIGHTS['price']
    
    # Площадь (вес 0.20)
    area_score = calculate_area_score(house_area, user_prefs.get('area', ''))
    score += area_score * WEIGHTS['area']
    
    # Этажи (вес 0.10)
    floors_score = calculate_floors_score(house['floors'], user_prefs.get('floors', ''))
    score += floors_score * WEIGHTS['floors']
    
    # Комнаты (вес 0.15)
    rooms_score = calculate_rooms_score(house['rooms'], user_prefs.get('rooms', ''))
    score += rooms_score * WEIGHTS['rooms']
    
    # Санузлы (вес 0.05)
    bathrooms_score = calculate_bathrooms_score(house['bathrooms'], user_prefs.get('bathrooms', ''))
    score += bathrooms_score * WEIGHTS['bathrooms']
    
    # Гараж (вес 0.05)
    garage_score = calculate_garage_score(house['garage'], user_prefs.get('garage', ''))
    score += garage_score * WEIGHTS['badges']
    
    # Материал (вес 0.10)
    material_score = calculate_material_score(house['material'], user_prefs.get('material', ''))
    score += material_score * WEIGHTS['material']
    
    # Стиль (вес 0.10)
    style_score = calculate_style_score(house['style'], user_prefs.get('style', ''))
    score += style_score * WEIGHTS['style']
    
    return round(score, 2)


def get_top_houses(user_prefs: Dict[str, str]) -> List[Dict]:
    """Возвращает топ-5 домов с их баллами"""
    houses = get_houses_list()
    
    houses_with_scores = []
    for house in houses:
        score = calculate_house_score(house, user_prefs)
        houses_with_scores.append({
            'house': house,
            'score': score
        })
    
    # Сортируем по убыванию баллов
    houses_with_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return houses_with_scores[:5]


def create_system_prompt(top_houses: List[Dict]) -> str:
    """Создает системный промпт с топ домами"""
    
    prompt = """Ты - эксперт по подбору загородных домов. Я уже рассчитал баллы соответствия для каждого дома (от 0 до 1, где 1 - идеальное совпадение).

Твоя задача - выбрать ТОП-3 дома из предложенных и объяснить клиенту, почему именно они подходят.

Топ-5 домов по баллам соответствия:

"""
    
    for idx, item in enumerate(top_houses, 1):
        house = item['house']
        score = item['score']
        prompt += f"{idx}. {house['name']} (Балл соответствия: {score})\n"
        prompt += f"   Цена: {house['price']}\n"
        prompt += f"   Площадь: {house['area']}\n"
        prompt += f"   Этажи: {house['floors']}\n"
        prompt += f"   Комнаты: {house['rooms']}\n"
        prompt += f"   Санузлы: {house['bathrooms']}\n"
        prompt += f"   Материал: {house['material']}\n"
        prompt += f"   Гараж: {house['garage']}\n"
        prompt += f"   Стиль: {house['style']}\n"
        prompt += f"   Особенности: {house['features']}\n\n"
    
    prompt += """
ВАЖНО: Выбери ТОЛЬКО 3 дома из этого списка. Учитывай баллы соответствия, но также обрати внимание на баланс цена/качество.

Ответ должен быть в следующем формате:

🏡 <b>Вариант 1: [Название дома]</b>
💰 Цена: [цена]
📐 Площадь: [площадь] | 🏠 Этажей: [этажи]
🚪 Комнат: [комнаты] | 🚿 Санузлов: [санузлы]

<i>Почему этот вариант:</i>
[Короткое объяснение в 2-3 предложениях, почему этот дом подходит клиенту. Упомяни конкретные совпадения с запросом]

[Аналогично для варианта 2 и 3]

Будь конкретным и объясняй выбор на основе реальных параметров.
"""
    
    return prompt


async def get_house_recommendations(user_preferences: Dict[str, str]) -> str:
    """Получает рекомендации домов через OpenAI API"""
    
    # Сначала считаем баллы и получаем топ-5
    top_houses = get_top_houses(user_preferences)
    
    user_request = f"""Подбери 3 лучших варианта дома для клиента со следующими предпочтениями:

Бюджет: {user_preferences.get('budget', 'не указан')}
Площадь: {user_preferences.get('area', 'не указана')}
Этажи: {user_preferences.get('floors', 'не важно')}
Комнаты: {user_preferences.get('rooms', 'не важно')}
Санузлы: {user_preferences.get('bathrooms', 'не важно')}
Материал: {user_preferences.get('material', 'не важно')}
Гараж: {user_preferences.get('garage', 'не важно')}
Стиль: {user_preferences.get('style', 'не важно')}

Баллы соответствия уже рассчитаны. Выбери 3 лучших варианта и объясни почему.
"""
    
    system_prompt = create_system_prompt(top_houses)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ],
        "max_tokens": OPENAI_MAX_TOKENS,
        "temperature": OPENAI_TEMPERATURE
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]