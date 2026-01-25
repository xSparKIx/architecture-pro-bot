import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any
import json
import uuid

class VectorStoreManager:
    def __init__(self, config: Dict[str, Any]):
        db_config = config['vector_db']
        self.db_type = db_config['type']
        self.persist_directory = db_config['persist_directory']
        self.collection_name = db_config['collection_name']
        self.batch_size = 1000  # Ограничиваем размер батча
        
        if self.db_type == "chromadb":
            self.setup_chromadb()
        elif self.db_type == "faiss":
            self.setup_faiss()
        else:
            raise ValueError(f"Неизвестный тип БД: {self.db_type}")
    
    def setup_chromadb(self):
        """Настройка ChromaDB"""
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Удаляем старую коллекцию если существует
        try:
            self.client.delete_collection(self.collection_name)
        except:
            pass
        
        # Создаем новую коллекцию
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 200,
                "hnsw:search_ef": 200,
                "hnsw:M": 16
            }
        )
    
    def create_index(self, chunks: List[Dict], embeddings: List[np.ndarray]):
        """Создание индекса в векторной БД с батчингом"""
        print(f"Создание индекса для {len(chunks)} чанков...")
        
        if self.db_type == "chromadb":
            # Разбиваем на батчи
            total_chunks = len(chunks)
            num_batches = (total_chunks + self.batch_size - 1) // self.batch_size
            
            for batch_idx in range(num_batches):
                start_idx = batch_idx * self.batch_size
                end_idx = min((batch_idx + 1) * self.batch_size, total_chunks)
                
                print(f"  Батч {batch_idx + 1}/{num_batches}: чанки {start_idx}-{end_idx}")
                
                # Подготовка данных для текущего батча
                batch_chunks = chunks[start_idx:end_idx]
                batch_embeddings = embeddings[start_idx:end_idx]
                
                ids = []
                documents = []
                metadatas = []
                embeddings_list = []
                
                for i, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                    # Генерируем уникальный ID
                    chunk_id = chunk["metadata"].get("chunk_id", str(uuid.uuid4()))
                    ids.append(chunk_id)
                    documents.append(chunk["text"])
                    
                    # Упрощаем метаданные (ChromaDB не любит сложные структуры)
                    simplified_metadata = {
                        "source": str(chunk["metadata"].get("source", "unknown"))[:500],
                        "type": str(chunk["metadata"].get("type", "unknown")),
                        "title": str(chunk["metadata"].get("title", ""))[:200],
                        "chunk_index": str(chunk["metadata"].get("chunk_index", 0))
                    }
                    metadatas.append(simplified_metadata)
                    
                    # Преобразуем numpy array в list
                    embeddings_list.append(embedding.tolist())
                
                # Добавляем батч в базу данных
                try:
                    self.collection.add(
                        embeddings=embeddings_list,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"    ✓ Добавлено {len(batch_chunks)} чанков")
                except Exception as e:
                    print(f"    ✗ Ошибка при добавлении батча: {str(e)}")
                    # Пробуем добавить по одному
                    self._add_one_by_one(ids, documents, metadatas, embeddings_list)
            
            print(f"Индекс создан в ChromaDB. Коллекция: {self.collection_name}")
            
            # Сохраняем информацию о коллекции
            info = {
                "collection_name": self.collection_name,
                "total_chunks": total_chunks,
                "embedding_dimension": embeddings[0].shape[0],
                "batch_size": self.batch_size,
                "persist_directory": self.persist_directory
            }
            
            with open(f"{self.persist_directory}/collection_info.json", 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
    
    def _add_one_by_one(self, ids, documents, metadatas, embeddings_list):
        """Добавление чанков по одному (fallback метод)"""
        print("Попытка добавления по одному...")
        success_count = 0
        
        for i in range(len(ids)):
            try:
                self.collection.add(
                    embeddings=[embeddings_list[i]],
                    documents=[documents[i]],
                    metadatas=[metadatas[i]],
                    ids=[ids[i]]
                )
                success_count += 1
                if success_count % 100 == 0:
                    print(f"    Добавлено {success_count} чанков...")
            except Exception as e:
                print(f"    Ошибка с чанком {ids[i]}: {str(e)[:100]}...")
                continue
        
        print(f"Итого добавлено: {success_count}/{len(ids)}")
    
    def search(self, query: str, top_k: int = 5, filter_dict: dict = None) -> List[Dict]:
        """Поиск по векторной БД"""
        if self.db_type == "chromadb":
            try:
                if filter_dict:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=top_k,
                        where=filter_dict,
                        include=["documents", "metadatas", "distances"]
                    )
                else:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=top_k,
                        include=["documents", "metadatas", "distances"]
                    )
                
                # Форматируем результаты
                formatted_results = []
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": 1 - results["distances"][0][i]  # Конвертируем расстояние в сходство
                    })
                
                return formatted_results
            except Exception as e:
                print(f"Ошибка при поиске: {e}")
                return []