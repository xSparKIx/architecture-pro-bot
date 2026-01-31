import os
import json
import sys
from pathlib import Path
from datetime import datetime
import csv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Добавляем путь к task6 в sys.path
task6_path = os.path.join(project_root, 'task6')
sys.path.insert(0, task6_path)

# Добавляем путь к task4 в sys.path
task4_path = os.path.join(project_root, 'task4')
sys.path.insert(0, task4_path)

LOGS_FILE = os.path.join(current_dir, 'logs.csv')
QUESTIONS_FILE = os.path.join(current_dir, 'golden_questions.json')

from update_index import run_once
from main import QuantumHelperCLI

def remove_key_entities_from_docs():
    """Удаляет ключевые сущности из документов для создания пробелов"""
    
    # Сущности для удаления
    entities_to_remove = [
        "Pajama Emperor",
        "Sudden Layoffs",
        "Emo Redemption Arc",
        "Lava Bath Planet",
    ]
    
    docs_path = Path(os.path.join(os.getcwd(), "task2/knowledge_base"))
    modified_files = []
    
    for file_path in docs_path.rglob("*.md"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Удаляем упоминания сущностей
            for entity in entities_to_remove:
                content = content.replace(entity, "[REDACTED]")
            
            # Если контент изменился, сохраняем
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files.append(str(file_path))
                print(f"Modified: {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Сохраняем информацию об удаленных сущностях для тестирования
    gaps_info = {
        "removed_entities": entities_to_remove,
        "modified_files": modified_files,
        "timestamp": "2024-01-27T10:00:00Z"
    }

    path = os.path.join(current_dir, "gaps_info.json")
    
    with open(path, "w") as f:
        json.dump(gaps_info, f, indent=2)
    
    print(f"\nCreated gaps in {len(modified_files)} files")
    return gaps_info

def test(bot: QuantumHelperCLI):
    '''Метод проверки работы бота'''

     # Тестовые запросы
    print("ТЕСТОВЫЕ ЗАПРОСЫ:")

    if os.path.exists(QUESTIONS_FILE):
        with open (QUESTIONS_FILE, encoding="utf-8") as file:
            questions = json.load(file)
    else:
        raise FileNotFoundError("Не найден файл с вопросами")

    for question in questions:
        _query(question=question["question"], bot=bot)

def _log(question: str, response: dict):
    '''Метод логирования результата выполнения запрос'''

    with open(LOGS_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                datetime.now().isoformat(),
                question,
                response["answer"],
                len(response["answer"]),
                response.get("sources", []),
                response["confidence"],
                response["documents_found"],
                "Да" if not response.get("is_unknown", False) else "Нет"
            ]
        )

def _query(question: str, bot: QuantumHelperCLI):
    '''Метод обработки вопросов'''

    response = bot.rag_pipeline.query(question)
    print(f'''
        Вопрос: {question};
        Уверенность: {response['confidence']};
        Найдено чанков: {response['documents_found']};
    ''')
    # Сохраняем лог
    _log(question, response)

if __name__ == "__main__":
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Время",
                    "Вопрос",
                    "Ответ",
                    "Длина ответа",
                    "Источники",
                    "Уверенность",
                    "Количество найденных чанков",
                    "Корректность"
                ]
            )

    # Удаляем данные из файлов
    remove_key_entities_from_docs()

    # Переиндексируем бд
    run_once()

    # Инициализируем бота
    bot = QuantumHelperCLI()

    # Тестируем вопросы
    test(bot)