from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import requests

load_dotenv()

# Токен от BotFather
TOKEN = os.getenv('TOKEN')
RAG_SERVICE_URL = os.getenv('RAG_SERVICE_URL')

print(f"Сервис: {RAG_SERVICE_URL}")

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот!")

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Доступные команды:\n/start - начать\n/help - помощь")

# Обработчик текстовых сообщений
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if not user_text:
        await update.message.reply_text(f"Пожалуйста, введите корректный вопрос")
        return

    print(f"Пользователь задал вопрос: {user_text}")

    try:
        data = { "question": user_text }
        await update.message.reply_text("Обрабатываю вопрос...")

        response = requests.post(f"{RAG_SERVICE_URL}/query", json=data)
        response_data = response.json()

        await update.message.reply_text(response_data["answer"])
    except Exception as e:
        print(e)
        await update.message.reply_text("Вовремя получения ответа произошла ошибка")

# Основная функция
def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()