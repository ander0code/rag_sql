"""Clientes LLM con fallback."""

import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_openai_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.ai.openai_model,
        temperature=settings.ai.temperature,
        streaming=True,
        openai_api_key=settings.ai.openai_api_key
    )


@lru_cache(maxsize=1)
def get_deepseek_llm() -> ChatOpenAI:
    return ChatOpenAI(
        temperature=settings.ai.temperature,
        model=settings.ai.deepseek_model,
        base_url="https://api.deepseek.com/v1",
        api_key=settings.ai.deepseek_api_key
    )


def get_available_llm() -> ChatOpenAI:
    if settings.ai.deepseek_api_key and settings.ai.deepseek_api_key.startswith('sk-'):
        try:
            llm = get_deepseek_llm()
            llm.invoke([HumanMessage(content="test")])
            logger.info("✅ Deepseek conectado")
            return llm
        except Exception as e:
            logger.warning(f"Deepseek falló: {str(e)[:50]}")
    
    if settings.ai.openai_api_key and settings.ai.openai_api_key.startswith('sk-'):
        try:
            llm = get_openai_llm()
            llm.invoke([HumanMessage(content="test")])
            logger.info("✅ OpenAI conectado")
            return llm
        except Exception as e:
            logger.error(f"OpenAI falló: {str(e)[:50]}")
    
    raise Exception("No hay LLM disponible")
