from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from dotenv import load_dotenv
import os
import json

load_dotenv('../.env')

class DocumentProcessor:

    def __init__(self, config: Dict[str, Any]):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(config['chunking']['chunk_size']),
            chunk_overlap=int(config['chunking']['chunk_overlap']),
            length_function=len,
            separators=config['chunking']['separators']
        )
    
    def split_documents(self, documents: List[Dict]) -> List[Dict]:
        """Разбивает документы на чанки с сохранением метаданных"""
        all_chunks = []

        # Получаем массив стоп-слов, по которым не будем включать документ в индекс
        stop_words_json = os.getenv('STOP_WORDS', '[]')

        # Преобразуем в список
        try:
            stop_words = json.loads(stop_words_json)
        except json.JSONDecodeError as e:
            print(f"Во время получения стоп-слов произошла ошибка {e}")
            stop_words = []  # значение по умолчанию при ошибке

        pattern = re.compile(r'(' + '|'.join(stop_words) + r')', re.IGNORECASE)
        
        for doc in documents:
            content = doc["content"]
            metadata = doc["metadata"]

            if re.search(pattern, content):
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