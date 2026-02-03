#!/bin/bash

# Сохраняем ВСЕ переменные окружения
printenv > /etc/environment

# Создаем cron задание с загрузкой переменных
echo "* * * * * . /etc/environment && cd /app && /usr/local/bin/python update_index.py >> /var/log/cron.log 2>&1" > /etc/cron.d/db-update

# Даем права на выполнение
chmod 0644 /etc/cron.d/db-update

# Применяем crontab
crontab /etc/cron.d/db-update

# Запускаем cron
echo "Starting cron..."
cron -f