from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from bot.langchain_rag import LangChainRAGPipeline
from config import CONFIG

app = FastAPI(
    title="QuantumHelper RAG API",
    description="RAG бот для внутренней базы знаний QuantumForge",
    version="1.0.0"
)

# Инициализация RAG пайплайна
rag_pipeline = LangChainRAGPipeline(CONFIG)

# Модели запросов/ответов
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    include_sources: Optional[bool] = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    reasoning: str
    confidence: float
    processing_time: float
    relevant_chunks: int

class HealthResponse(BaseModel):
    status: str
    vector_db_ready: bool
    llm_ready: bool
    total_conversations: int

@app.get("/", tags=["Health"])
async def root():
    return {"message": "QuantumHelper RAG API работает"}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Проверка статуса системы"""
    # Здесь можно добавить реальные проверки
    return {
        "status": "healthy",
        "vector_db_ready": True,
        "llm_ready": True,
        "total_conversations": len(rag_pipeline.conversation_history)
    }

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """Обработка запроса пользователя"""
    try:
        # Обработка через RAG пайплайн
        response = rag_pipeline.process_query(request.question)
        
        return QueryResponse(
            answer=response["answer"],
            sources=response["sources"],
            reasoning=response["reasoning"],
            confidence=response["confidence"],
            processing_time=0.0,  # Можно добавить реальное время
            relevant_chunks=response["relevant_chunks"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", tags=["History"])
async def get_conversation_history(limit: int = 10):
    """Получение истории диалогов"""
    return {
        "conversations": rag_pipeline.conversation_history[-limit:],
        "total": len(rag_pipeline.conversation_history)
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)