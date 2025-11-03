FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование общих модулей
COPY core ./core
COPY models ./models
COPY services ./services
COPY utils ./utils

# Копирование кода бота
COPY bot ./bot

# Создание директорий для данных и логов
RUN mkdir -p /app/data /app/logs

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV DOCKER_ENV=true

# Команда запуска
CMD ["python", "-m", "bot.start_bot"]
