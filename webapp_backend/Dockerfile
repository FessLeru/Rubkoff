FROM python:3.12-slim

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
COPY webapp_backend/requirements.txt ./webapp_backend_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r webapp_backend_requirements.txt

# Копирование общих модулей
COPY core ./core
COPY models ./models
COPY services ./services
COPY utils ./utils

# Копирование кода бэкенда
COPY webapp_backend ./webapp_backend

# Создание директорий для данных и логов
RUN mkdir -p /app/data /app/logs

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV DOCKER_ENV=true

# Команда запуска
CMD ["uvicorn", "webapp_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
