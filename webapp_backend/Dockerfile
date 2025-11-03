FROM python:3.12-slim

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Копирование общих модулей из корневой директории
COPY ../core ./core
COPY ../models ./models
COPY ../services ./services
COPY ../utils ./utils

# Создание директорий для данных и логов
RUN mkdir -p /app/data /app/logs

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV DOCKER_ENV=true

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
