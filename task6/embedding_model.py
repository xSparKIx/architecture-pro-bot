import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import numpy as np

class EmbeddingGenerator:

    def __init__(self, config: Dict[str, Any]):
        self.model_name = config['model_name']
        self.dimension = config['dimension']
        self.max_length = config['max_length']
        self.device = config['device']
        
        print(f"Загрузка модели эмбеддингов: {self.model_name}")
        
        # Загрузка модели
        self.model = SentenceTransformer(
            self.model_name,
            device=self.device
        )
        
        # Оптимизация для CPU/GPU
        if self.device == "cpu":
            self.model = self.model.to(torch.device("cpu"))
            # Используем float32 для CPU
            self.model.encode(["test"], convert_to_tensor=True)
        else:
            self.model = self.model.to(torch.device("cuda"))
            # Используем float16 для GPU для экономии памяти
            self.model.half()
        
        print(f"Модель загружена на {self.device}")
    
    def embed_batch(self, chunks: List[Dict]) -> List[np.ndarray]:
        """Генерация эмбеддингов для батча чанков"""
        texts = [chunk["text"] for chunk in chunks]
        
        # Кодирование с учетом максимальной длины
        embeddings = self.model.encode(
            texts,
            batch_size=len(texts),
            show_progress_bar=False,
            convert_to_tensor=True,
            normalize_embeddings=True,  # Важно для косинусного сходства
            device=self.device
        )
        
        # Конвертируем в numpy для сохранения
        if embeddings.is_cuda:
            embeddings = embeddings.cpu().numpy()
        else:
            embeddings = embeddings.numpy()
        
        return embeddings
    
    def get_model_info(self) -> Dict[str, Any]:
        """Информация о модели"""
        return {
            "name": self.model_name,
            "dimension": self.dimension,
            "max_length": self.max_length,
            "device": self.device,
            "vocab_size": getattr(self.model, 'vocab_size', 'unknown')
        }