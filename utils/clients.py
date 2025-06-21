import logging
from functools import lru_cache
from qdrant_client import QdrantClient
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from config.settings import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Obtiene un cliente singleton de Qdrant"""
    logger.info(f"Inicializando cliente Qdrant: {settings.vector_db.url}")
    return QdrantClient(url=settings.vector_db.url)

@lru_cache(maxsize=1)
def get_embeddings_model() -> OpenAIEmbeddings:
    """Obtiene un modelo singleton de embeddings"""
    logger.info("Inicializando modelo de embeddings OpenAI")
    return OpenAIEmbeddings(openai_api_key=settings.ai.openai_api_key)

@lru_cache(maxsize=1)
def get_openai_llm() -> ChatOpenAI:
    """Obtiene un modelo singleton de OpenAI LLM"""
    logger.info(f"Inicializando modelo OpenAI: {settings.ai.openai_model}")
    return ChatOpenAI(
        model=settings.ai.openai_model,
        temperature=settings.ai.temperature,
        streaming=True,
        openai_api_key=settings.ai.openai_api_key
    )

@lru_cache(maxsize=1)
def get_deepseek_llm() -> ChatOpenAI:
    """Obtiene un modelo singleton de Deepseek LLM"""
    logger.info(f"Inicializando modelo Deepseek: {settings.ai.deepseek_model}")
    return ChatOpenAI(
        temperature=settings.ai.temperature,
        model=settings.ai.deepseek_model,
        base_url="https://api.deepseek.com/v1",
        api_key=settings.ai.deepseek_api_key
    )