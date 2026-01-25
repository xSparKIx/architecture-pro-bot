#!/usr/bin/env python3
import sys
from colorama import init, Fore
from bot.langchain_rag import LangChainRAGPipeline
from config import CONFIG

init(autoreset=True)  # Инициализация colorama

class QuantumHelperCLI:
    def __init__(self):
        print(Fore.CYAN + "🤖 Инициализация QuantumHelper RAG Bot...")
        try:
            self.rag_pipeline = LangChainRAGPipeline(CONFIG)
            print(Fore.GREEN + "✅ Система инициализирована успешно!")
        except Exception as e:
            print(Fore.RED + f"❌ Ошибка инициализации: {e}")
            print(Fore.YELLOW + "\nВозможные решения:")
            print(Fore.YELLOW + "1. Убедитесь, что векторная БД создана (запустите build_index.py)")
            print(Fore.YELLOW + "2. Проверьте установленные зависимости")
            print(Fore.YELLOW + "3. Для Ollama: запустите 'ollama serve' в отдельном терминале")
            sys.exit(1)
    
    def run(self):
        """Основной цикл CLI"""
        print(Fore.CYAN + "=" * 60)
        print(Fore.CYAN + "🤖 QuantumHelper - RAG Assistant for QuantumForge")
        print(Fore.CYAN + "=" * 60)
        print(Fore.YELLOW + "Техники промптинга: Few-shot + Chain-of-Thought")
        print(Fore.YELLOW + "Введите вопрос или 'выход' для завершения")
        print()
        
        # Предустановленные вопросы для тестирования
        test_questions = [
            "Who is it Furry Growler?",
            "What do you know about Ice Cube Planet?",
            "Where ara from Motherfucker?",
        ]
        
        print(Fore.MAGENTA + "📋 Примеры вопросов для тестирования:")
        for i, q in enumerate(test_questions, 1):
            print(Fore.WHITE + f"  {i}. {q}")
        
        while True:
            try:
                print(Fore.BLUE + "\n➤ Ваш вопрос: ", end="")
                question = input().strip()
                
                if question.lower() in ['выход', 'exit', 'quit', 'q']:
                    print(Fore.GREEN + "\n👋 До свидания!")
                    break
                
                if not question:
                    continue
                
                # Обработка запроса
                print(Fore.CYAN + "\n🔍 Обработка запроса...")
                response = self.rag_pipeline.query(question)
                
                # Вывод ответа
                print(Fore.GREEN + "\n📋 ОТВЕТ:")
                print(Fore.WHITE + response["answer"])
                
                if response.get("sources"):
                    print(Fore.YELLOW + "\n🔍 ИСТОЧНИКИ:")
                    for i, source in enumerate(response["sources"], 1):
                        print(Fore.YELLOW + f"  {i}. {source}")
                
                print(Fore.CYAN + f"\n🎯 Уверенность: {response['confidence']:.2f}")
                print(Fore.CYAN + f"📊 Найдено чанков: {response['documents_found']}")
                
                # Сохраняем скриншоты для задания
                self._save_for_screenshot(question, response)
                
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\n\n👋 Прервано пользователем")
                break
            except Exception as e:
                print(Fore.RED + f"\n❌ Ошибка: {e}")
    
    def _save_for_screenshot(self, question: str, response: dict):
        """Сохранение диалога"""
        import json
        from datetime import datetime
        
        # Создаем директорию для скриншотов
        import os
        os.makedirs("screenshots", exist_ok=True)
        
        # Сохраняем диалог
        dialog = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": response["answer"][:500] + "..." if len(response["answer"]) > 500 else response["answer"],
            "sources": response.get("sources", []),
            "confidence": response["confidence"],
            "documents_found": response["documents_found"],
            "is_unknown": response.get("is_unknown", False)
        }
        
        # Сохраняем в файл
        filename = f"screenshots/dialog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dialog, f, indent=2, ensure_ascii=False)
        
        print(Fore.MAGENTA + f"\n💾 Диалог сохранен в: {filename}")

if __name__ == "__main__":
    cli = QuantumHelperCLI()
    cli.run()