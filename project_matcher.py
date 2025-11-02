"""Сопоставление проектов из rubkoff_projects.json с предпочтениями пользователя"""
import json
from typing import Dict, List


def parse_area_from_project(area_str: str) -> int:
    """Извлекает площадь из строки проекта"""
    try:
        # Пример: "593 м²" -> 593
        return int(area_str.split()[0])
    except:
        return 0


def parse_floors_from_project(floors_str: str) -> int:
    """Извлекает количество этажей из строки проекта"""
    try:
        # Пример: "2 этажа" -> 2
        return int(floors_str.split()[0])
    except:
        return 1


def parse_rooms_from_project(rooms_str: str) -> int:
    """Извлекает количество спален из строки проекта"""
    try:
        # Пример: "4" -> 4
        return int(rooms_str)
    except:
        return 0


def parse_bathrooms_from_project(bathrooms_str: str) -> int:
    """Извлекает количество санузлов из строки проекта"""
    try:
        # Пример: "2" -> 2
        return int(bathrooms_str)
    except:
        return 1


def match_user_area(project_area: int, user_area: str) -> float:
    """Проверяет соответствие площади"""
    if not user_area or user_area == "не важно":
        return 1.0
    
    try:
        # Парсим диапазон из "150-200 м²" или "300+ м²"
        if "-" in user_area:
            min_area, max_area = map(int, user_area.replace("м²", "").split("-"))
            if min_area <= project_area <= max_area:
                return 1.0
            # Если близко к диапазону, даем частичный балл
            if project_area < min_area:
                return max(0.5, 1.0 - (min_area - project_area) / min_area * 0.5)
            else:
                return max(0.5, 1.0 - (project_area - max_area) / max_area * 0.5)
        elif "+" in user_area:
            min_area = int(user_area.replace("м²", "").replace("+", ""))
            if project_area >= min_area:
                return 1.0
            return max(0.5, project_area / min_area)
        else:
            # Точно указанная площадь
            target_area = int(user_area.replace("м²", ""))
            diff = abs(project_area - target_area)
            return max(0.0, 1.0 - diff / target_area * 0.5)
    except:
        return 0.5


def match_user_floors(project_floors: int, user_floors: str) -> float:
    """Проверяет соответствие этажности"""
    if not user_floors or user_floors == "не важно" or user_floors == "any":
        return 1.0
    
    try:
        # Парсим "1", "2", "3" или "any"
        user_floors_int = int(user_floors)
        if project_floors == user_floors_int:
            return 1.0
        # Если разница в 1 этаж, даем 0.7 балла
        if abs(project_floors - user_floors_int) == 1:
            return 0.7
        return 0.3
    except:
        return 0.5


def match_user_rooms(project_rooms: int, user_rooms: str) -> float:
    """Проверяет соответствие количества комнат"""
    if not user_rooms or user_rooms == "не важно":
        return 1.0
    
    try:
        # Парсим "2", "3", "4", "5+" и т.д.
        if "+" in user_rooms:
            min_rooms = int(user_rooms.replace("+", ""))
            if project_rooms >= min_rooms:
                return 1.0
            return max(0.5, project_rooms / min_rooms)
        else:
            user_rooms_int = int(user_rooms)
            if project_rooms == user_rooms_int:
                return 1.0
            # Если разница в 1 комнату, даем 0.7 балла
            if abs(project_rooms - user_rooms_int) == 1:
                return 0.7
            return 0.3
    except:
        return 0.5


def match_user_bathrooms(project_bathrooms: int, user_bathrooms: str) -> float:
    """Проверяет соответствие количества санузлов"""
    if not user_bathrooms or user_bathrooms == "не важно" or user_bathrooms == "any":
        return 1.0
    
    try:
        if "+" in user_bathrooms:
            min_bathrooms = int(user_bathrooms.replace("+", ""))
            if project_bathrooms >= min_bathrooms:
                return 1.0
            return max(0.5, project_bathrooms / min_bathrooms)
        else:
            user_bathrooms_int = int(user_bathrooms)
            if project_bathrooms == user_bathrooms_int:
                return 1.0
            if abs(project_bathrooms - user_bathrooms_int) == 1:
                return 0.7
            return 0.3
    except:
        return 0.5


def calculate_project_score(project: Dict, user_prefs: Dict[str, str]) -> float:
    """Рассчитывает балл соответствия проекта предпочтениям пользователя"""
    score = 0.0
    weights = {
        'area': 0.3,
        'floors': 0.2,
        'rooms': 0.25,
        'bathrooms': 0.15,
        'style': 0.1
    }
    
    characteristics = project.get("characteristics", {})
    
    # Площадь
    project_area_str = characteristics.get("Площадь", "0 м²")
    project_area = parse_area_from_project(project_area_str)
    area_score = match_user_area(project_area, user_prefs.get('area', ''))
    score += area_score * weights['area']
    
    # Этажность
    project_floors_str = characteristics.get("Этажность", "1 этаж")
    project_floors = parse_floors_from_project(project_floors_str)
    floors_score = match_user_floors(project_floors, user_prefs.get('floors', ''))
    score += floors_score * weights['floors']
    
    # Комнаты (спальни)
    project_rooms_str = characteristics.get("Кол-во спален", "0")
    project_rooms = parse_rooms_from_project(project_rooms_str)
    rooms_score = match_user_rooms(project_rooms, user_prefs.get('rooms', ''))
    score += rooms_score * weights['rooms']
    
    # Санузлы
    project_bathrooms_str = characteristics.get("Кол-во санузлов", "1")
    project_bathrooms = parse_bathrooms_from_project(project_bathrooms_str)
    bathrooms_score = match_user_bathrooms(project_bathrooms, user_prefs.get('bathrooms', ''))
    score += bathrooms_score * weights['bathrooms']
    
    # Стиль (упрощенная проверка по описанию)
    style_score = 0.5  # Базовый балл
    user_style = user_prefs.get('style', '').lower()
    if user_style and user_style != "any":
        project_desc = (project.get("description", "") + " " + project.get("title", "")).lower()
        if user_style in project_desc:
            style_score = 1.0
        elif "современный" in user_style and any(word in project_desc for word in ["современный", "хай-тек", "модерн"]):
            style_score = 0.8
        elif "классический" in user_style and any(word in project_desc for word in ["классический", "классика"]):
            style_score = 0.8
    score += style_score * weights['style']
    
    return round(score, 2)


def get_recommended_projects(user_prefs: Dict[str, str], limit: int = 3) -> List[Dict]:
    """Возвращает список рекомендованных проектов из rubkoff_projects.json"""
    try:
        with open("rubkoff_projects.json", "r", encoding="utf-8") as f:
            all_projects = json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки rubkoff_projects.json: {e}")
        return []
    
    # Рассчитываем баллы для каждого проекта
    projects_with_scores = []
    for project in all_projects:
        score = calculate_project_score(project, user_prefs)
        projects_with_scores.append({
            'project': project,
            'score': score
        })
    
    # Сортируем по убыванию баллов
    projects_with_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # Возвращаем топ-N проектов
    return [item['project'] for item in projects_with_scores[:limit]]

