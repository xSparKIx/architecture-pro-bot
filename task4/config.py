import os
from dotenv import load_dotenv

load_dotenv('../.env')

CONFIG = {
    # Модель эмбеддингов
    "embedding_model": {
        "name": os.getenv('EMBEDDING_MODEL'),
        "device": os.getenv('EMBEDDING_DEVICE')
    },
    
    # Векторная БД
    "vector_db": {
        "persist_directory": os.path.join(os.getcwd(), os.getenv('VECTOR_DB_DIRECTORY')),
        "collection_name": os.getenv('COLLECTION_NAME')
    },
    
    # LLM для генерации ответов
    "llm": {
        "type": "local",  # "openai" или "local"
        "model_name": os.getenv('MODEL_NAME'),
        "base_url": os.getenv('OLLAMA_URL')
    },
    
    # Параметры RAG
    "rag": {
        "top_k": 3,
        "min_relevance_score": 0.3
    }
}