#!/bin/bash

set -e  # Останавливать скрипт при ошибках

echo "=== Настройка локального окружения для RAG-бота ==="

# 1. Проверка Python
echo "[1/5] Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен. Установите: sudo apt install python3 python3-venv"
    exit 1
fi

# 2. Создание виртуального окружения
echo "[2/5] Создание виртуального окружения..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Виртуальное окружение создано"
else
    echo "⏩ Виртуальное окружение уже существует"
fi

# Активация venv
source .venv/bin/activate

# 3. Установка зависимостей Python
echo "[3/5] Установка зависимостей Python..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Зависимости установлены"
else
    echo "⚠️  Во время установки произошла ошибка"
    exit 1
fi

# 4. Проверка и установка Ollama
echo "[4/5] Настройка Ollama..."

# Проверяем, установлен ли Ollama
if command -v ollama &> /dev/null; then
    echo "✅ Ollama уже установлен"
else
    echo "Установка Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Проверяем успешность установки
    if command -v ollama &> /dev/null; then
        echo "✅ Ollama успешно установлен"
    else
        echo "❌ Не удалось установить Ollama"
        exit 1
    fi
fi

# 5. Запуск Ollama сервера и загрузка модели
echo "[5/5] Запуск Ollama и загрузка модели..."

# Проверяем, запущен ли сервер Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Запуск сервера Ollama в фоне..."
    # Запускаем ollama в фоне
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo $OLLAMA_PID > /tmp/ollama.pid
    echo "✅ Сервер Ollama запущен (PID: $OLLAMA_PID)"
    
    # Ждем запуска сервера
    echo "Ожидание запуска сервера..."
    sleep 10
    
    # Проверяем запуск
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Сервер Ollama готов"
    else
        echo "❌ Не удалось запустить сервер Ollama"
        echo "Проверьте логи: tail -f /tmp/ollama.log"
        exit 1
    fi
else
    echo "⏩ Сервер Ollama уже запущен"
fi

# Проверяем, есть ли уже модель mistral
echo "Проверка наличия модели mistral..."
if ollama list | grep -q "mistral"; then
    echo "✅ Модель mistral уже загружена"
else
    echo "Загрузка модели mistral:7b-instruct..."
    ollama pull mistral:7b-instruct

    # Проверяем успешность загрузки
    if ollama list | grep -q "mistral"; then
        echo "✅ Модель mistral успешно загружена"
    else
        echo "⚠️  Не удалось загрузить модель mistral"
        echo "Попробуйте легкую модель: ollama pull llama3.2:1b"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "✅ Настройка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Отредактируйте .env файл"
echo "2. Запустите RAG сервис:"
echo "   source .venv/bin/activate"
echo "   python task4/main.py"
echo "3. Запустите Telegram бота:"
echo "   source .venv/bin/activate"
echo "   python etc/tg_bot/main.py"
echo ""
echo "Для остановки Ollama сервера:"
echo "   kill \$(cat /tmp/ollama.pid) 2>/dev/null || pkill ollama"
echo "========================================="