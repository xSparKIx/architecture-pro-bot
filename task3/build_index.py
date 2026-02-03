import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Импорт наших модулей
from chunking import DocumentProcessor
from embedding_model import EmbeddingGenerator
from vector_store import VectorStoreManager

load_dotenv('../.env')

# Конфигурация
CONFIG = {
    # Модель эмбеддингов (выбор из задания 1)
    "embedding_model": {
        "name": os.getenv('EMBEDDING_MODEL'),
        "repo": os.getenv('EMBEDDING_REPO'),
        "dimension": os.getenv('EMBEDDING_DIMENSION'),
        "max_length": 512,
        "device": os.getenv('EMBEDDING_DEVICE')
    },
    
    # Параметры чанкинга
    "chunking": {
        "chunk_size": os.getenv("CHUNK_SIZE"),
        "chunk_overlap": os.getenv("CHUNK_OVERLAP"),
        "separators": ["\n\n", "\n", ". ", " ", ""]
    },
    
    # Векторная БД
    "vector_db": {
        "type": os.getenv('VECTOR_DB'),  # или "faiss"
        "persist_directory": os.path.join(os.getcwd(), os.getenv('VECTOR_DB_DIRECTORY')),
        "collection_name": os.getenv('COLLECTION_NAME')
    },
    
    # Пути к данным
    "data_paths": {
        "markdown": os.path.join(os.getcwd(), "task2/knowledge_base"),
    },
    
    # Параметры обработки
    "batch_size": 32
}

#todo поправить зависимости python
class VectorIndexBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processor = DocumentProcessor(config)
        self.embedder = EmbeddingGenerator(config)
        self.vector_store = VectorStoreManager(config)

        # Логирование
        self.log_file = "indexing_log.json"
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "total_chunks": 0,
            "total_documents": 0,
            "processing_time": 0,
            "model_info": {}
        }
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """Загрузка документов из различных источников"""
        documents = []
        
        # 1. Markdown/MDX файлы
        md_path = Path(self.config['data_paths']['markdown'])

        if md_path.exists():
            for md_file in md_path.rglob("*.md"):
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append({
                        "content": content,
                        "metadata": {
                            "source": str(md_file),
                            "type": "markdown",
                            "title": md_file.stem,
                            "path": str(md_file.relative_to(md_path))
                        }
                    })
        
        self.stats["total_documents"] = len(documents)
        print(f"Загружено документов: {len(documents)}")
        return documents
    
    def process_and_index(self):
        """Основной процесс индексации"""
        print("=" * 60)
        print("НАЧАЛО ИНДЕКСАЦИИ ВЕКТОРНОЙ БАЗЫ ЗНАНИЙ")
        print("=" * 60)
        
        # Шаг 1: Загрузка документов
        print("[1/4] Загрузка документов...")
        documents = self.load_documents()
        
        # Шаг 2: Разбиение на чанки
        print("[2/4] Разбиение на чанки...")
        chunks = self.processor.split_documents(documents)
        self.stats["total_chunks"] = len(chunks)
        print(f"Создано чанков: {len(chunks)}")
        
        # Шаг 3: Генерация эмбеддингов
        print("[3/4] Генерация эмбеддингов...")
        start_embedding = time.time()
        
        embeddings = []
        chunk_batch = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_batch.append(chunk)
            
            # Пакетная обработка для эффективности
            if len(chunk_batch) >= self.config['batch_size'] or i == len(chunks):
                batch_embeddings = self.embedder.embed_batch(chunk_batch)
                embeddings.extend(batch_embeddings)
                chunk_batch = []
                
                # Прогресс
                if i % 100 == 0 or i == len(chunks):
                    print(f"  Обработано: {i}/{len(chunks)} чанков")
        
        embedding_time = time.time() - start_embedding
        self.stats["embedding_time"] = embedding_time
        print(f"Генерация эмбеддингов завершена за {embedding_time:.2f} сек")
        
        # Шаг 4: Сохранение в векторную БД
        print("[4/4] Сохранение в векторную БД...")
        self.vector_store.create_index(chunks, embeddings)
        
        # Сохранение статистики
        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["processing_time"] = time.time() - start_embedding
        self.stats["model_info"] = self.embedder.get_model_info()
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        print("=" * 60)
        print("ИНДЕКСАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        print(f"Итоговая статистика сохранена в {self.log_file}")
        print("=" * 60)
        
        return self.stats

if __name__ == "__main__":
    # Создание директорий
    os.makedirs("./index", exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    
    # Запуск индексации
    builder = VectorIndexBuilder(CONFIG)
    stats = builder.process_and_index()
    
    # Тестовые запросы
    print("\nТЕСТОВЫЕ ЗАПРОСЫ:")
    test_queries = [
        "Who is it Motherfucker?",
        "Who is it Tails of the Jedi Tanos?",
        "Who parents of Tails of the Jedi Tanos?",
        "Where are Tails of the Jedi Tanos from?",
        "Who is it Cookie Hunter?"
    ]
    
    for query in test_queries:
        results = builder.vector_store.search(query, top_k=3)
        print(f"\nЗапрос: '{query}'")

        for i, result in enumerate(results, 1):
            print(f"{result}")
            print(f"  {i}. {result['metadata']['source'][:50]}... (сходство: {result['score']:.3f})")