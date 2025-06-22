# Rubkoff House Selection Bot

Telegram бот для подбора домов от компании Rubkoff с интеграцией **xtunnel.ru** для локального тестирования. Бот использует GPT для интеллектуального подбора домов на основе предпочтений пользователя.

## ✨ Возможности

- 🤖 **Telegram Bot** с поддержкой Mini App
- 🌐 **Web API** с FastAPI  
- 🏠 **Система рекомендаций домов**
- 📱 **Telegram Mini App** интерфейс
- 🎯 **GPT-4 интеграция** для умных рекомендаций
- 📊 **Система администрирования**
- 🔄 **Парсинг данных** с сайта Rubkoff
- 💾 **База данных** SQLite/PostgreSQL
- 🔗 **XTunnel.ru** интеграция для внешнего доступа

## 🚀 Быстрый старт

### ⚡ Вариант 1: Локальное тестирование (проще всего!)

Самый простой способ протестировать приложение:

```bash
# Windows - одна команда
test_local.bat

# Linux/Mac
python xtunnel_server.py
```

**🎉 Готово! Доступ к приложению:**
- 📱 **Mini App**: http://127.0.0.1:8000/frontend/
- 🔗 **API**: http://127.0.0.1:8000/api
- ❤️ **Health Check**: http://127.0.0.1:8000/api/health

### 🎯 Вариант 1.5: Полный запуск (Bot + Mini App + XTunnel)

Запуск Telegram бота в Mock режиме + Mini App через XTunnel:

```bash
# Windows - автонастройка .env + запуск
start_run_both.bat

# Linux/Mac/Windows - прямой запуск
python run_both.py
```

**Что запускается:**
- 🤖 **Telegram Bot** в Mock режиме (быстрый подбор)
- 🌐 **Mini App** через XTunnel.ru
- 📱 **Доступ**: https://ваш_поддомен.xtunnel.ru/frontend/

**Настройка .env для XTunnel:**
```env
XTUNNEL_API_KEY=ваш_ключ_с_xtunnel_ru
XTUNNEL_SUBDOMAIN=my-rubkoff-app
BOT_TOKEN=ваш_телеграм_бот_токен
```

### 🌐 Вариант 2: XTunnel.ru (для внешнего доступа)

Если нужен доступ из интернета для Telegram:

1. **Получите доступ к XTunnel:**
   - Зайдите на https://cabinet.xtunnel.ru/
   - Зарегистрируйтесь и получите API ключ
   - Получите поддомен для вашего приложения

2. **Настройте переменные окружения:**
```bash
# Windows
set XTUNNEL_API_KEY=ваш_ключ_здесь
set XTUNNEL_SUBDOMAIN=ваш_поддомен

# Linux/Mac
export XTUNNEL_API_KEY=ваш_ключ_здесь
export XTUNNEL_SUBDOMAIN=ваш_поддомен
```

3. **Запустите сервер:**
```bash
# Windows
start_xtunnel.bat

# Linux/Mac
python xtunnel_server.py
```

4. **🎉 Доступ через интернет:**
   - 📱 **Mini App**: https://ваш_поддомен.xtunnel.ru/frontend/
   - 🔗 **API**: https://ваш_поддомен.xtunnel.ru/api

### 🔧 Настройка .env

Для работы с Telegram ботом создайте `.env`:
```bash
# Скопируйте и отредактируйте
copy env-sample .env
```

## 📁 Структура проекта

```
rubkoff/
├── xtunnel_server.py           # 🔗 Основной сервер с XTunnel
├── local_test_server.py        # 💻 Локальный тест сервер
├── main.py                     # 🤖 Telegram Bot
├── start_xtunnel.bat          # 🚀 Запуск Windows
├── app/
│   ├── core/                   # ⚙️ Конфигурация
│   ├── models/                 # 📊 Модели данных
│   ├── services/               # 🎯 Бизнес-логика
│   ├── bot/                    # 🤖 Telegram обработчики
│   ├── utils/                  # 🔧 Утилиты
│   └── api/                    # 🌐 API для Mini App
└── frontend/                   # 📱 Mini App интерфейс
    ├── index.html
    ├── styles.css
    ├── script.js
    └── assets/
```

## ⚙️ Конфигурация

Основные настройки в `.env`:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321

# OpenAI GPT
OPENAI_API_KEY=your_openai_api_key

# XTunnel.ru (опционально)
XTUNNEL_API_KEY=ваш_ключ_здесь
XTUNNEL_SUBDOMAIN=ваш_поддомен

# Режим работы
MOCK_MODE=false  # true для тестирования без GPT
```

## 🎯 Архитектура подбора домов

### Production Mode (с GPT)

1. **Инициализация** - Пользователь нажимает "Подобрать дом 🏠"
2. **Интерактивный опрос** - GPT задает вопросы о предпочтениях
3. **Анализ предпочтений** - GPT анализирует ответы
4. **Подбор дома** - Система находит наиболее подходящий дом
5. **Результат** - Отправляется информация о доме

### Mock Mode (для тестирования)

1. **Мгновенный подбор** - Выбирается случайный дом из БД
2. **Результат** - Показывается с кнопкой "Открыть приложение"

## 🌐 API Endpoints

**GET /api/health**
- Проверка состояния API

**GET /api/houses**
- Список всех домов

**GET /api/houses/{house_id}**
- Детали конкретного дома

**GET /api/user/{user_id}/recommendations**
- Персональные рекомендации

**GET /api/houses/mock/recommendations**
- Случайные дома для тестирования

## 📱 Mini App Features

- 🏠 **Просмотр домов** - Карточки с фото и характеристиками
- ⭐ **Система оценок** - Recommendation scores и match reasons
- 🔍 **Фильтрация** - По цене, площади, количеству комнат
- 📊 **Статистика** - Отслеживание просмотров
- 💬 **Обратная связь** - Интеграция с Telegram

## 🛠️ Технологии

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy
- **Bot**: aiogram 3.x
- **AI**: OpenAI GPT API
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **Tunnel**: XTunnel.ru для внешнего доступа

## 🔧 Разработка

### Требования
- Python 3.8+
- Telegram Bot Token
- OpenAI API Key (для production)
- XTunnel.ru аккаунт (для внешнего доступа)

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### База данных
```bash
python migrate_db.py  # Применить миграции
```

## 📝 Логи

Сервер создает логи в файлах:
- `xtunnel_server.log` - Основной сервер
- `bot.log` - Telegram bot
- `local_server.log` - Локальный тест сервер

## 🤝 Поддержка

Для вопросов по настройке XTunnel.ru:
- 📖 Документация: https://cabinet.xtunnel.ru/
- 💬 Поддержка через личный кабинет

## 📄 Лицензия

MIT License - используйте свободно для своих проектов.