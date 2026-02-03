# Используем легкий образ Python с установленным cron
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем cron и необходимые утилиты
RUN apt-get update && apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем папку для данных
RUN mkdir -p /app/chroma_data /app/knowledge_base

# Копируем cron задание
# Создаем простой скрипт для запуска
RUN echo '#!/bin/bash\ncd /app && python update_index.py' > /app/run_update.sh && \
    chmod +x /app/run_update.sh

# Создаем лог файл
RUN touch /var/log/cron.log

# Устанавливаем правильные права для cron логов
RUN chmod 666 /var/log/cron.log

# Копируем entrypoint скрипт
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]