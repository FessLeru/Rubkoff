from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_budget_kb():
    buttons = [
        [InlineKeyboardButton(text="💵 10-13 млн", callback_data="budget_10-13")],
        [InlineKeyboardButton(text="💵 13-17 млн", callback_data="budget_13-17")],
        [InlineKeyboardButton(text="💵 17-25 млн", callback_data="budget_17-25")],
        [InlineKeyboardButton(text="💵 25+ млн", callback_data="budget_25+")],
        [InlineKeyboardButton(text="✏️ Свой вариант", callback_data="budget_custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_area_kb():
    buttons = [
        [InlineKeyboardButton(text="📏 100-150 м²", callback_data="area_100-150")],
        [InlineKeyboardButton(text="📏 150-200 м²", callback_data="area_150-200")],
        [InlineKeyboardButton(text="📏 200-300 м²", callback_data="area_200-300")],
        [InlineKeyboardButton(text="📏 300+ м²", callback_data="area_300+")],
        [InlineKeyboardButton(text="✏️ Свой вариант", callback_data="area_custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_floors_kb():
    buttons = [
        [InlineKeyboardButton(text="1️⃣ Одноэтажный", callback_data="floors_1")],
        [InlineKeyboardButton(text="2️⃣ Двухэтажный", callback_data="floors_2")],
        [InlineKeyboardButton(text="3️⃣ Трехэтажный", callback_data="floors_3")],
        [InlineKeyboardButton(text="🤷 Не важно", callback_data="floors_any")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_rooms_kb():
    buttons = [
        [InlineKeyboardButton(text="2 комнаты", callback_data="rooms_2")],
        [InlineKeyboardButton(text="3 комнаты", callback_data="rooms_3")],
        [InlineKeyboardButton(text="4 комнаты", callback_data="rooms_4")],
        [InlineKeyboardButton(text="5+ комнат", callback_data="rooms_5+")],
        [InlineKeyboardButton(text="✏️ Свой вариант", callback_data="rooms_custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_bathrooms_kb():
    buttons = [
        [InlineKeyboardButton(text="1 санузел", callback_data="bathrooms_1")],
        [InlineKeyboardButton(text="2 санузла", callback_data="bathrooms_2")],
        [InlineKeyboardButton(text="3+ санузла", callback_data="bathrooms_3+")],
        [InlineKeyboardButton(text="🤷 Не важно", callback_data="bathrooms_any")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_material_kb():
    buttons = [
        [InlineKeyboardButton(text="🧱 Камень", callback_data="material_brick")],
        [InlineKeyboardButton(text="🪵 Дерево", callback_data="material_wood")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_garage_kb():
    buttons = [
        [InlineKeyboardButton(text="✅ Да, нужен гараж", callback_data="garage_yes")],
        [InlineKeyboardButton(text="❌ Не нужен", callback_data="garage_no")],
        [InlineKeyboardButton(text="🤷 Не важно", callback_data="garage_any")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_style_kb():
    buttons = [
        [InlineKeyboardButton(text="🏛️ Классический", callback_data="style_classic")],
        [InlineKeyboardButton(text="🌆 Современный", callback_data="style_modern")],
        [InlineKeyboardButton(text="🏔️ Шале", callback_data="style_chalet")],
        [InlineKeyboardButton(text="🇺s Американский", callback_data="style_american")],
        [InlineKeyboardButton(text="🌿 Скандинавский", callback_data="style_scandinavian")],
        [InlineKeyboardButton(text="🤷 Не важно", callback_data="style_any")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)