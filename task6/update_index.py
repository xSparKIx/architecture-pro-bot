#!/usr/bin/env python3
"""
Скрипт обновления с сравнением хешей
Сравнивает хеши файлов и обновляет только измененные
"""

import os
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from index_helper import BuildIndex

load_dotenv('../.env')

# Конфигурация
CONFIG = {
    "source_folder": os.path.join(os.getcwd(), os.getenv('KNOWLEDGE_BASE')),                # Папка с документами
    "persist_directory": os.path.join(os.getcwd(), os.getenv("VECTOR_DB_DIRECTORY")),       # Папка с документами
    "state_file": os.path.join(os.getcwd(), "update_state.json"),                     # Файл состояния
    "log_file": os.path.join(os.getcwd(), "update_log.txt"),                          # Файл логов
    "check_interval": int(os.getenv("CHECK_INTERVAL", '86400')),                            # Интервал актуализации логов
    "collection_name": os.getenv("COLLECTION_NAME"),                                        # Имя коллекции в ChromaDB
    "embedding_model": os.getenv("EMBEDDING_MODEL"),                                        # Модель эмбеддингов
    "chunk_size": int(os.getenv("CHUNK_SIZE")),                                             # Размер чанка
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP")),                                       # Перекрытие чанков
    "summary_file": os.path.join(os.getcwd(), "update_summary.json"),
    "device": os.getenv("EMBEDDING_DEVICE"),
    "vector_db_type": os.getenv('VECTOR_DB'),
}

def setup_logging():
    """Настройка логирования"""
    log_dir = Path(CONFIG["log_file"]).parent
    log_dir.mkdir(parents=True, exist_ok=True)

def log_message(message, level="INFO"):
    """Запись сообщения в лог"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    print(log_entry)
    
    with open(CONFIG["log_file"], "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def load_state():
    """Загрузка состояния обновления"""
    state_file = Path(CONFIG["state_file"])
    
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_message(f"Ошибка загрузки состояния: {e}", "WARNING")
    
    # Состояние по умолчанию
    return {
        "last_update": None,
        "file_hashes": {},  # format: {"file_path": "hash", ...}
        "total_chunks": 0
    }

def save_state(state):
    """Сохранение состояния обновления"""
    state["last_update"] = datetime.now().isoformat()
    
    state_file = Path(CONFIG["state_file"])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def calculate_file_hash(file_path):
    """Вычисление MD5 хеша файла"""
    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Читаем файл по частям
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()  # Возвращаем строку
    except Exception as e:
        log_message(f"Ошибка чтения {file_path}: {e}", "WARNING")
        return None

def find_changed_files(state):
    """
    Поиск измененных файлов
    Возвращает список файлов, которые изменились с последнего обновления
    """
    source_path = Path(CONFIG["source_folder"])
    
    if not source_path.exists():
        log_message(f"Папка {CONFIG['source_folder']} не найдена. Создаю...", "INFO")
        source_path.mkdir(parents=True, exist_ok=True)
        return []
    
    changed_files = []
    
    # Загружаем хеши из состояния
    old_hashes = state.get("file_hashes", {})
    
    # Ищем все текстовые файлы
    for ext in ['*.txt', '*.md']:
        for file_path in source_path.rglob(ext):
            if file_path.is_file():
                file_str = str(file_path)
                
                # Вычисляем текущий хеш файла
                current_hash = calculate_file_hash(file_path)
                
                if current_hash is None:
                    continue  # Пропускаем файлы, которые не удалось прочитать
                
                # Получаем старый хеш из состояния
                old_hash = old_hashes.get(file_str)
                
                # Сравниваем хеши
                if old_hash != current_hash:
                    # Файл изменился или новый
                    status = "new" if old_hash is None else "modified"
                    changed_files.append({
                        "path": file_str,
                        "hash": current_hash,
                        "status": status,
                        "old_hash": old_hash  # для отладки
                    })
                    
                    # Обновляем хеш в состоянии
                    old_hashes[file_str] = current_hash
                    log_message(f"Хеш обновлен для {file_path.name}: {old_hash} -> {current_hash}", "DEBUG")
                else:
                    log_message(f"Файл не изменился: {file_path.name}", "DEBUG")
    
    # Также проверяем удаленные файлы
    current_files = set()
    for ext in ['*.txt', '*.md']:
        for file_path in source_path.rglob(ext):
            if file_path.is_file():
                current_files.add(str(file_path))
    
    # Удаляем из состояния файлы, которых больше нет
    files_to_remove = []
    for file_str in list(old_hashes.keys()):
        if file_str not in current_files:
            files_to_remove.append(file_str)
            log_message(f"Файл удален из источника: {Path(file_str).name}", "INFO")
    
    for file_str in files_to_remove:
        del old_hashes[file_str]
    
    # Сохраняем обновленные хеши обратно в состояние
    state["file_hashes"] = old_hashes
    state["files_to_remove"] = files_to_remove
    
    return changed_files, files_to_remove

def build_index(changed_files=[], files_to_remove=[]) -> int:
    """Метод переиндексации измененных файлов"""
    
    if not changed_files and not files_to_remove:
        log_message("Не передано файлов для переиндексации")
        return 0

    # Получаем массив стоп-слов, по которым не будем включать документ в индекс
    stop_words_json = os.getenv('STOP_WORDS', '[]')

    # Преобразуем в список
    try:
        stop_words = json.loads(stop_words_json)
    except json.JSONDecodeError as e:
        print(f"Во время получения стоп-слов произошла ошибка {e}")
        stop_words = []  # значение по умолчанию при ошибке

    # Переиндексирусем измененные чанки
    builder = BuildIndex({
        "model_name": CONFIG["embedding_model"],
        "dimension": os.getenv("EMBEDDING_DIMENSION"),
        "device": CONFIG["device"],
        "db_type": CONFIG["vector_db_type"],
        "persist_directory": CONFIG["persist_directory"],
        "collection_name": CONFIG["collection_name"],
        "chunk_size": CONFIG["chunk_size"],
        "chunk_overlap": CONFIG["chunk_overlap"],
        "stop_words": stop_words,
        "batch_size": 32
    })

    return builder.rebuild(changed_files, files_to_remove)

def run_update():
    """Основная функция обновления"""
    log_message("=" * 50)
    log_message("АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ БАЗЫ ЗНАНИЙ")
    log_message("=" * 50)

    start_time = time.time()

    # Загружаем состояние
    state = load_state()
    last_update = state.get("last_update", "никогда")
    log_message(f"Последнее обновление: {last_update}")
    log_message(f"Файлов отслеживается: {len(state.get('file_hashes', {}))}")
    
    # Ищем измененные файлы
    changed_files, files_to_remove = find_changed_files(state)
    
    if not changed_files and not files_to_remove:
        log_message("Нет изменений в документах")
        # Все равно сохраняем состояние (обновляем время)
        save_state(state)
        return
    
    log_message(f"Найдено измененных файлов: {len(changed_files)}")
    log_message(f"Найдено файлов для удаления: {len(files_to_remove)}")

    # Симулируем индексацию
    total_chunks = build_index(changed_files, files_to_remove)
    
    # Обновляем статистику
    state["total_chunks"] = total_chunks
    
    # Сохраняем состояние (включая обновленные хеши)
    save_state(state)
    
    # Логируем результат
    duration = time.time() - start_time
    
    log_message("=" * 50)
    log_message("ИТОГИ ОБНОВЛЕНИЯ:")
    log_message(f"  Время выполнения: {duration:.2f} сек")
    log_message(f"  Всего чанков в базе: {state['total_chunks']}")
    log_message(f"  Файлов отслеживается: {len(state['file_hashes'])}")
    log_message("=" * 50)
    
    # Сохраняем сводку
    save_summary(changed_files, total_chunks, duration, state)

def save_summary(files, chunks, duration, state):
    """Сохранение сводки обновления"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "files_processed": len(files),
        "chunks_created": chunks,
        "duration_seconds": round(duration, 2),
        "tracked_files_count": len(state.get("file_hashes", {})),
        "file_list": [
            {
                "path": f["path"],
                "status": f["status"],
                "hash": f["hash"],
                "old_hash": f.get("old_hash")
            } for f in files
        ]
    }
    
    with open(Path(CONFIG["summary_file"]), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    log_message(f"Сводка сохранена в update_summary.json")

def run_once():
    """Однократный запуск обновления"""
    setup_logging()
    
    # Запускаем обновление
    run_update()

def run_daemon():
    """Запуск в режиме демона (проверка по расписанию)"""
    setup_logging()
    
    log_message("🚀 ЗАПУСК ОБНОВЛЕНИЯ")
    log_message(f"Папка с документами: {CONFIG['source_folder']}")
    log_message(f"Проверка каждые: {CONFIG['check_interval'] // 3600} часов")
    log_message("=" * 50)
    
    update_count = 0
    
    try:
        while True:
            update_count += 1
            log_message(f"Цикл обновления #{update_count}")
            
            run_update()
            
            log_message(f"Следующая проверка через {CONFIG['check_interval'] // 3600} часов...")
            time.sleep(CONFIG["check_interval"])
    except KeyboardInterrupt:
        log_message("Демон остановлен пользователем", "INFO")

if __name__ == "__main__":
    # Выберите режим запуска:
    run_once()     # Один раз для тестирования
    # run_daemon()  # Режим для production