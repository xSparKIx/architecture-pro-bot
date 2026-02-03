FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN cat requirements.txt

# Копируем исходный код
COPY . .

# Создаем папку для данных
RUN mkdir -p /app/chroma_data

# Проверяем что Python установлен
RUN which python && python --version

# Команда для запуска бота
CMD ["python", "api.py"]