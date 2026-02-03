import os
import json
import sys
from pathlib import Path
from datetime import datetime
import csv
from typing import List, Dict, Any
import re
from pathlib import Path

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
        _query(question=question, bot=bot)

def calculate_confidence(
    answer: str, 
    doc_count: int, 
    sources: List[str] = None, 
    query: str = None,
    golden_question: Dict = None
) -> float:
    """
    Расчет уверенности с проверкой источников и ключевых слов.
    
    Args:
        answer: Ответ бота
        doc_count: Количество найденных документов
        sources: Список источников
        query: Исходный запрос
        golden_question: Данные golden question (если есть)
    
    Returns:
        Confidence score от 0.1 до 1.0
    """
    # Базовая уверенность
    base_confidence = 0.3
    
    # 1. Учет количества документов (с меньшим весом)
    if doc_count > 0:
        doc_boost = min(doc_count * 0.05, 0.2)
        base_confidence += doc_boost
    
    # 2. Проверка релевантности источников (самый важный фактор)
    if sources:
        source_score = _calculate_source_score(sources, query, golden_question)
        base_confidence += source_score
    
    # 3. Проверка ключевых слов в ответе
    if golden_question and golden_question.get("keywords"):
        keyword_score = _calculate_keyword_score(answer, golden_question["keywords"])
        base_confidence += keyword_score
    
    # 4. Штраф за слова сомнения (обновленный список)
    doubt_penalty = _calculate_doubt_penalty(answer)
    base_confidence *= doubt_penalty
    
    # 5. Дополнительные проверки
    base_confidence = _apply_additional_checks(base_confidence, answer, doc_count)
    
    return round(max(0.1, min(base_confidence, 1.0)), 2)

def _calculate_source_score(
    sources: List[str], 
    query: str, 
    golden_question: Dict = None
) -> float:
    """Оценка релевантности источников"""
    if not sources:
        return -0.3  # Сильный штраф за отсутствие источников
    
    score = 0.0
    query_lower = query.lower() if query else ""
    query_words = set(query_lower.split())
    
    # Проверка по golden question (если есть)
    if golden_question and golden_question.get("expected_sources"):
        expected_sources = golden_question["expected_sources"]
        
        # Проверяем, есть ли ожидаемые источники в найденных
        found_expected = 0
        for expected in expected_sources:
            expected_lower = expected.lower()
            if any(expected_lower in s.lower() for s in sources):
                found_expected += 1
        
        # Бонус за нахождение ожидаемых источников
        expected_ratio = found_expected / len(expected_sources) if expected_sources else 0
        if expected_ratio > 0:
            score += expected_ratio * 0.4  # До +0.4 за полное соответствие
    
    # Проверка релевантности по ключевым словам запроса
    relevant_count = 0
    for source in sources:
        source_name = Path(source).stem.lower()
        
        # Проверяем совпадение с запросом
        if any(word in source_name for word in query_words if len(word) > 3):
            relevant_count += 1
        
        # Проверяем по ключевым словам golden question
        if golden_question and golden_question.get("keywords"):
            keywords = golden_question["keywords"]
            if any(keyword in source_name for keyword in keywords):
                relevant_count += 1
    
    # Расчет релевантности
    relevance_ratio = relevant_count / len(sources)
    
    if relevance_ratio >= 0.8:
        score += 0.3
    elif relevance_ratio >= 0.5:
        score += 0.1
    elif relevance_ratio >= 0.2:
        score += 0.0
    else:
        score -= 0.2  # Штраф за нерелевантные источники
    
    return score

def _calculate_keyword_score(answer: str, expected_keywords: List[str]) -> float:
    """Проверка наличия ключевых слов в ответе"""
    if not expected_keywords:
        return 0.0
    
    answer_lower = answer.lower()
    found_keywords = 0
    
    for keyword in expected_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in answer_lower:
            found_keywords += 1
    
    keyword_ratio = found_keywords / len(expected_keywords)
    
    # Маппинг ratio в score
    if keyword_ratio >= 0.8:
        return 0.2
    elif keyword_ratio >= 0.5:
        return 0.1
    elif keyword_ratio >= 0.3:
        return 0.05
    else:
        return -0.1  # Штраф за отсутствие ключевых слов

def _calculate_doubt_penalty(answer: str) -> float:
    """Штраф за слова сомнения и неуверенности"""
    doubt_patterns = [
        # Русские
        r'\bне могу\b', r'\bне знаю\b', r'\bнет информации\b',
        r'\bне уверен\b', r'\bвозможно\b', r'\bвероятно\b',
        r'\bможет быть\b', r'\bпредполагаю\b', r'\bсложно сказать\b',
        r'\bнедостаточно данных\b', r'\bтребуется дополнительн\b',
        r'\bисточник не предоставлен\b',
        
        # Английские
        r'\bI don\'?t know\b', r'\bno information\b', r'\bcannot provide\b',
        r'\bwithout providing\b', r'\bneed more context\b', r'\badditional information\b',
        r'\bmaybe\b', r'\bperhaps\b', r'\bprobably\b', r'\bnot sure\b',
    ]
    
    answer_lower = answer.lower()
    penalty = 1.0
    
    for pattern in doubt_patterns:
        if re.search(pattern, answer_lower):
            # Разный штраф в зависимости от серьезности
            if pattern in [r'\bне могу\b', r'\bне знаю\b', r'\bI don\'?t know\b']:
                penalty *= 0.3  # Сильный штраф
            elif pattern in [r'\bнет информации\b', r'\bno information\b']:
                penalty *= 0.4
            else:
                penalty *= 0.7  # Легкий штраф
    
    return penalty

def _apply_additional_checks(confidence: float, answer: str, doc_count: int) -> float:
    """Дополнительные проверки для корректировки confidence"""
    
    # 1. Очень короткий ответ без документов
    if len(answer) < 100 and doc_count == 0:
        confidence *= 0.5
    
    # 2. Явный ответ "Я не знаю"
    not_know_patterns = [
        r'Извините, я не могу найти информацию',
        r'не могу найти информацию по вопросу',
        r'в текущей базе знаний нет информации',
        r'информация не найдена',
    ]
    
    for pattern in not_know_patterns:
        if re.search(pattern, answer, re.IGNORECASE):
            return 0.1  # Фиксированный низкий confidence
    
    # 3. Ответ содержит противоречия
    if _contains_contradictions(answer):
        confidence *= 0.6
    
    return confidence

def _contains_contradictions(answer: str) -> bool:
    """Проверка на противоречия в ответе"""
    contradictions = [
        ("не знаю", "но"),
        ("нет информации", "однако"),
        ("не могу найти", "скорее всего"),
    ]
    
    answer_lower = answer.lower()
    for neg, conj in contradictions:
        if neg in answer_lower and conj in answer_lower:
            # Проверяем, что они в одном предложении
            sentences = re.split(r'[.!?]', answer_lower)
            for sentence in sentences:
                if neg in sentence and conj in sentence:
                    return True
    
    return False

def _get_unknown_response(question: str) -> Dict[str, Any]:
    """Стандартный ответ для неизвестных вопросов"""
    reasoning = """РАЗМЫШЛЕНИЕ:
1. Проанализировал запрос: '{question}'
2. Поискал в базе знаний
3. Не нашел релевантной информации
4. Нужно честно признать, что не знаю ответа"""
    
    answer = f"""{reasoning}

ОТВЕТ:
Извините, я не могу найти информацию по вопросу '{question}' в текущей базе знаний QuantumForge."""

    return {
        "answer": answer.replace("{question}", question),
        "sources": [],
        "reasoning": reasoning.replace("{question}", question),
        "confidence": 0.1,
        "documents_found": 0,
        "is_unknown": True
    }

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

def _query(question, bot: QuantumHelperCLI):
    '''Метод обработки вопросов'''

    result = {}
    response = bot.rag_pipeline.query(question["question"])

    # Пересчитываем точность с учетом проверочного вопроса
    confidence = calculate_confidence(
        answer=response["answer"],
        doc_count=response["documents_found"],
        sources=response["sources"],
        query=question["question"],
        golden_question=question
    )

    if confidence > 0.5:
        result = response
        result["confidence"] = confidence
    else:
        result = _get_unknown_response(question=question["question"])

    print(f'''
        Вопрос: {question["question"]};
        Уверенность: {result["confidence"]};
        Найдено чанков: {result['documents_found']};
    ''')

    # Сохраняем лог
    _log(question=question["question"], response=result)

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