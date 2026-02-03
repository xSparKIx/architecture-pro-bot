from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Dict, Any
from pathlib import Path
import re
import time
from embedding_model import EmbeddingGenerator
from vector_store import VectorStoreManager

class BuildIndex:
    """@todo Обьединить с модулем из 3его задания"""

    def __init__(self, config: Dict[str, Any]):
        self.batch_size = config["batch_size"]
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.vector_db = VectorStoreManager({
            "db_type": config["db_type"],
            "persist_directory": config["persist_directory"],
            "collection_name": config["collection_name"],
        })
        self.embedder = EmbeddingGenerator({
            "model_name": config["model_name"],
            "dimension": config["dimension"],
            "max_length": 512,
            "device": config["device"],
        })

        stop_words = config["stop_words"] or []
        self.stop_pattern = re.compile(r'(' + '|'.join(stop_words) + r')', re.IGNORECASE)

    def rebuild(self, files, files_to_remove) -> int:
        if not files and not files_to_remove:
            return self.vector_db.count()

        # Удаляем старые версии и файлы для удаления
        paths_to_remove = files_to_remove.copy()

        # Собираем список измененных файлов
        for file in files:
            paths_to_remove.append(file["path"])

        doc = self.vector_db.get(where={"source": { "$in": paths_to_remove }})
        doc_ids = doc["ids"]

        if doc_ids:
            self.vector_db.delete(doc_ids)

        documents = self._load_documents(files)

        if not documents:
            return self.vector_db.count()

        chunks = self._split_documents(documents)
        
        start_embedding = time.time()
        
        embeddings = []
        chunk_batch = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_batch.append(chunk)
            
            # Пакетная обработка для эффективности
            if len(chunk_batch) >= self.batch_size or i == len(chunks):
                batch_embeddings = self.embedder.embed_batch(chunk_batch)
                embeddings.extend(batch_embeddings)
                chunk_batch = []
                
                # Прогресс
                if i % 100 == 0 or i == len(chunks):
                    print(f"  Обработано: {i}/{len(chunks)} чанков")
        
        embedding_time = time.time() - start_embedding
        print(f"Генерация эмбеддингов завершена за {embedding_time:.2f} сек")

        self.vector_db.create_index(chunks, embeddings)

        return self.vector_db.count()
    
    def _load_documents(self, files):
        documents = []

        for file in files:
            # Конвертируем в Path объект
            path = Path(file["path"]) if isinstance(file["path"], str) else file["path"]

            if not path.exists():
                continue

            if path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append({
                        "content": content,
                        "metadata": {
                            "source": str(path),
                            "type": "markdown",
                            "title": path.stem,
                            "path": path.resolve()
                        }
                    })

        return documents

    def _split_documents(self, documents):
        """Разбивает документы на чанки с сохранением метаданных"""
        all_chunks = []
        
        for doc in documents:
            content = doc["content"]
            metadata = doc["metadata"]

            if re.search(self.stop_pattern, content):
                title = str(metadata.get("title", ""))
                print(f"Документ {title} потенциально опасный и был исключен из индекса")
                continue
            
            # Используем рекурсивное разбиение
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{metadata['source']}_chunk_{i}".replace("/", "_").replace("\\", "_")
                
                # Упрощаем метаданные для ChromaDB
                chunk_data = {
                    "text": chunk_text,
                    "metadata": {
                        "id": chunk_id,
                        "source": str(metadata.get("source", "unknown")),
                        "type": str(metadata.get("type", "unknown")),
                        "title": str(metadata.get("title", "")),
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                }
                all_chunks.append(chunk_data)
        
        return all_chunks
    
    def _generate_embeddings(self, chunks):
        if not chunks:
            return

        start_embedding = time.time()
        embeddings = []
        chunk_batch = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_batch.append(chunk)
            
            # Пакетная обработка для эффективности
            if len(chunk_batch) >= 32 or i == len(chunks):
                batch_embeddings = self.embedder.embed_batch(chunk_batch)
                embeddings.extend(batch_embeddings)
                chunk_batch = []
                
                # Прогресс
                if i % 100 == 0 or i == len(chunks):
                    print(f"  Обработано: {i}/{len(chunks)} чанков")
        
        embedding_time = time.time() - start_embedding

        print(f"Генерация эмбеддингов завершена за {embedding_time:.2f} сек")

        return embeddings, chunk_batch