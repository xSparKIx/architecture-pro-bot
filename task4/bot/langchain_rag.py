import os
from typing import List, Dict, Any
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOpenAI
from bot.prompt_templates import get_cot_few_shot_prompt_template
from dotenv import load_dotenv
import re
import json

load_dotenv('../../.env')

class LangChainRAGPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vector_store = self._setup_vector_store()
        self.llm = self._setup_llm()
        self.qa_chain = self._setup_qa_chain()
        self.conversation_history = []
    
    def _setup_vector_store(self):
        """Настройка векторного хранилища"""
        embedding_config = self.config['embedding_model']
        
        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_config['name'],
            model_kwargs={'device': embedding_config.get('device', 'cpu')},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        vector_store_config = self.config['vector_db']
        
        # Проверяем существование директории
        os.makedirs(vector_store_config['persist_directory'], exist_ok=True)
        
        # Загружаем векторную БД
        try:
            vector_store = Chroma(
                persist_directory=vector_store_config['persist_directory'],
                collection_name=vector_store_config['collection_name'],
                embedding_function=embeddings
            )
            count = vector_store._collection.count()

            print(f"✅ Векторное хранилище загружено. Документов: {count}")

            return vector_store
        except Exception as e:
            print(f"⚠️  Не удалось загрузить векторную БД: {e}")
            print("Создаю новую коллекцию...")
            return Chroma(
                persist_directory=vector_store_config['persist_directory'],
                collection_name=vector_store_config['collection_name'],
                embedding_function=embeddings
            )
    
    def _setup_llm(self):
        """Настройка LLM"""
        llm_config = self.config['llm']
        
        if llm_config['type'] == 'openai':
            return ChatOpenAI(
                model=llm_config.get('model_name', 'gpt-3.5-turbo'),
                temperature=0.1,
                max_tokens=1000,
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
        
        elif llm_config['type'] == 'local':
            try:
                return Ollama(
                    model=llm_config.get('model_name', os.getenv('MODEL_NAME')),
                    base_url=llm_config.get('base_url', os.getenv('OLLAMA_URL')),
                    temperature=0.1,
                    num_predict=500
                )
            except Exception as e:
                raise RuntimeError(f"⚠️ Не удалось подключиться к Ollama: {e}")
        
        else:
            raise TypeError("⚠️ Неизвестный тип LLM")
    
    def _setup_qa_chain(self):
        """Настройка QA цепи с промптингом"""
        
        # Создаем промпт с Few-shot и Chain-of-Thought
        prompt_template = get_cot_few_shot_prompt_template()
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Создаем retriever
        retriever = self.vector_store.as_retriever(
            search_kwargs={
                "k": self.config['rag'].get('top_k', 3),
            }
        )
        
        # Создаем QA цепь с использованием invoke
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={
                "prompt": prompt,
                "verbose": False
            },
            return_source_documents=True
        )
        
        return qa_chain

    def query(self, question: str) -> Dict[str, Any]:
        """Обработка запроса пользователя"""
        try:
            # Получаем массив стоп-слов, по которым не будем включать документ в индекс
            stop_words_json = os.getenv('STOP_WORDS', '[]')

            # Преобразуем в список
            try:
                stop_words = json.loads(stop_words_json)
            except json.JSONDecodeError as e:
                print(f"Во время получения стоп-слов произошла ошибка {e}")
                stop_words = []  # значение по умолчанию при ошибке

            pattern = re.compile(r'(' + '|'.join(stop_words) + r')', re.IGNORECASE)

            # Если в тексте есть стоп-слово, то преостанавливаем обработку
            if re.search(pattern, question):
                return self._get_unknown_response(question)

            # Используем invoke вместо прямого вызова
            result = self.qa_chain.invoke({"query": question})

            # Извлекаем результат
            answer = result.get("result", "Нет ответа")
            source_documents = result.get("source_documents", [])
            
            # Если нет документов или короткий ответ - это случай "не знаю"
            if not source_documents or len(answer) < 50 or "не знаю" in answer.lower():
                return self._get_unknown_response(question)
            
            # Извлекаем информацию
            sources = self._extract_sources(source_documents)
            reasoning = self._extract_reasoning(answer)
            confidence = self._calculate_confidence(answer, len(source_documents))

            # Если не уверен хотябы на 50% то не знаем ответа
            if confidence < 0.5:
                return self._get_unknown_response(question)
            
            response = {
                "answer": answer,
                "sources": sources,
                "reasoning": reasoning,
                "confidence": confidence,
                "documents_found": len(source_documents),
                "is_unknown": False
            }
            
            # Сохраняем в историю
            self.conversation_history.append((question, answer))
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка при обработке запроса: {e}")
            return self._get_unknown_response(question)
    
    def _extract_sources(self, source_documents: List) -> List[str]:
        """Извлечение источников из документов"""
        sources = []
        for doc in source_documents:
            if hasattr(doc, 'metadata'):
                source = doc.metadata.get('source', 'Неизвестный источник')
                if source and source not in sources:
                    sources.append(source)
        return sources[:3]
    
    def _extract_reasoning(self, answer: str) -> str:
        """Извлечение цепочки рассуждений из ответа"""
        lines = answer.split('\n')
        reasoning_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['размышление', 'шаг', 'сначала', 'затем', 'поэтому', '1.', '2.', '3.']):
                reasoning_lines.append(line.strip())
        
        if reasoning_lines:
            return "\n".join(reasoning_lines[:5])  # Ограничиваем 5 строками
        
        # Если явного reasoning нет, берем начало ответа
        return answer[:200] + "..."
    
    def _calculate_confidence(self, answer: str, doc_count: int) -> float:
        """Расчет уверенности на основе ответа и количества документов"""
        # Базовая уверенность на основе длины ответа
        base_confidence = min(len(answer) / 500, 0.7)
        
        # Увеличиваем если нашли документы
        if doc_count > 0:
            base_confidence += min(doc_count * 0.1, 0.3)
        
        # Уменьшаем если есть слова сомнения
        doubt_words = [
            'возможно',
            'вероятно',
            'может быть',
            'не уверен',
            'предполагаю',
            'definitive answer',
            'cannot provide',
            'additional context',
            'provide more information',
            'accurate answer',
            'I don\'t know',
            'no information',
            'without providing',
            'I must analyze',
            'I must provide an answer based on',
            'maybe',
            'perhaps',
            'probably',
            'not sure',
            "don't know",
        ]
        if any(word in answer.lower() for word in doubt_words):
            base_confidence *= 0.7
        
        return round(min(base_confidence, 1.0), 2)
    
    def _get_unknown_response(self, question: str) -> Dict[str, Any]:
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