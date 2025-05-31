"""Constants and messages for the bot"""

# Command descriptions
START_COMMAND = "🏠 Начать подбор дома"
HELP_COMMAND = "❓ Помощь"
ADMIN_COMMAND = "👑 Панель администратора"
BROADCAST_COMMAND = "📢 Создать рассылку"
STATS_COMMAND = "📊 Статистика"
UPDATE_CATALOG_COMMAND = "🔄 Обновить каталог"

# Messages
WELCOME_MESSAGE = """
👋 Здравствуйте! Я помогу вам подобрать идеальный дом от компании Rubkoff.

Я задам несколько вопросов о ваших предпочтениях и предложу наиболее подходящие варианты.

Чтобы начать подбор, нажмите кнопку "{START_COMMAND}"
"""

HELP_MESSAGE = """
🤖 Я бот для подбора домов от компании Rubkoff.

Основные команды:
/start - Начать подбор дома
/help - Показать это сообщение
/admin - Панель администратора (для админов)

При подборе дома я учитываю:
• Желаемую площадь
• Количество этажей
• Планировку
• Бюджет
• Дополнительные пожелания

Я использую искусственный интеллект для наилучшего подбора вариантов! 🎯
"""

ADMIN_WELCOME = """
👑 <b>Панель администратора</b>

Доступные действия:
• {BROADCAST_COMMAND}
• {STATS_COMMAND}
• {UPDATE_CATALOG_COMMAND}
"""

BROADCAST_START = "📢 Отправьте сообщение для рассылки всем пользователям:"
BROADCAST_CONFIRM = "📋 Предпросмотр сообщения:\n\n{message}\n\nОтправить?"
BROADCAST_SUCCESS = "✅ Рассылка успешно отправлена {count} пользователям"
BROADCAST_CANCEL = "❌ Рассылка отменена"

UPDATE_CATALOG_START = "🔄 Начинаю обновление каталога домов..."
UPDATE_CATALOG_SUCCESS = "✅ Каталог успешно обновлен! Добавлено {count} домов"
UPDATE_CATALOG_ERROR = "❌ Ошибка при обновлении каталога: {error}"

# Error messages
ERROR_NOT_ADMIN = "❌ У вас нет прав администратора"
ERROR_GENERAL = "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору"
ERROR_NO_HOUSES = "❌ К сожалению, не удалось найти подходящие дома. Попробуйте изменить критерии поиска"
ERROR_INVALID_HOUSE = "❌ Дом не найден"

# Button texts
BUTTON_YES = "✅ Да"
BUTTON_NO = "❌ Нет"
BUTTON_CANCEL = "🚫 Отмена"
BUTTON_BACK = "⬅️ Назад"
BUTTON_MORE = "📝 Подробнее"
BUTTON_RESTART = "🔄 Начать заново"
BUTTON_WEBSITE = "🌐 Перейти на сайт"

# Regex patterns
PHONE_PATTERN = r'^\+?[78][-\(]?\d{3}\)?-?\d{3}-?\d{2}-?\d{2}$'
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Other constants
MAX_DESCRIPTION_LENGTH = 1000
MIN_AREA = 50
MAX_AREA = 500
MIN_PRICE = 1_000_000
MAX_PRICE = 50_000_000 