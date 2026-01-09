# Fábrica de LLM - Soporte multi-proveedor
# Proveedores: deepseek, openai, claude, groq, gemini, ollama

import logging
from functools import lru_cache
from typing import AsyncIterator, List, Any
from config.settings import settings
from utils.logging import token_counter
from core.ports.llm_port import LLMPort

logger = logging.getLogger(__name__)


class LLMWrapper(LLMPort):
    """Wrapper de LLM con conteo de tokens - Implementa LLMPort"""

    def __init__(self, llm, provider: str, model: str):
        self.llm = llm
        self.provider = provider
        self.model = model

    def invoke(self, messages: List[Any]) -> Any:
        """Invocación síncrona"""
        input_text = " ".join(m.content for m in messages if hasattr(m, "content"))
        response = self.llm.invoke(messages)
        output_text = (
            response.content if hasattr(response, "content") else str(response)
        )
        token_counter.track(input_text, output_text, f"{self.provider}/{self.model}")
        return response

    async def ainvoke(self, messages: List[Any]) -> Any:
        """Invocación asíncrona"""
        input_text = " ".join(m.content for m in messages if hasattr(m, "content"))
        response = await self.llm.ainvoke(messages)
        output_text = (
            response.content if hasattr(response, "content") else str(response)
        )
        token_counter.track(input_text, output_text, f"{self.provider}/{self.model}")
        return response

    async def astream(self, messages: List[Any]) -> AsyncIterator[str]:
        """Stream asíncrono de tokens"""
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

    def get_model_name(self) -> str:
        """Retorna nombre del modelo"""
        return f"{self.provider}/{self.model}"


def _get_deepseek() -> LLMWrapper:
    from langchain_openai import ChatOpenAI

    model = settings.ai.llm_model or settings.ai.deepseek_model
    llm = ChatOpenAI(
        temperature=settings.ai.temperature,
        model=model,
        base_url="https://api.deepseek.com/v1",
        api_key=settings.ai.deepseek_api_key,
        max_tokens=settings.ai.max_tokens_response,
    )
    logger.info(f"LLM: Deepseek ({model})")
    return LLMWrapper(llm, "deepseek", model)


def _get_openai() -> LLMWrapper:
    from langchain_openai import ChatOpenAI

    model = settings.ai.llm_model or settings.ai.openai_model
    llm = ChatOpenAI(
        model=model,
        temperature=settings.ai.temperature,
        openai_api_key=settings.ai.openai_api_key,
        max_tokens=settings.ai.max_tokens_response,
    )
    logger.info(f"LLM: OpenAI ({model})")
    return LLMWrapper(llm, "openai", model)


def _get_claude() -> LLMWrapper:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "Instala langchain-anthropic: pip install langchain-anthropic"
        )

    model = settings.ai.llm_model or settings.ai.anthropic_model
    llm = ChatAnthropic(
        model=model,
        temperature=settings.ai.temperature,
        anthropic_api_key=settings.ai.anthropic_api_key,
        max_tokens=settings.ai.max_tokens_response,
    )
    logger.info(f"LLM: Claude ({model})")
    return LLMWrapper(llm, "claude", model)


def _get_groq() -> LLMWrapper:
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError("Instala langchain-groq: pip install langchain-groq")

    model = settings.ai.llm_model or settings.ai.groq_model
    llm = ChatGroq(
        model=model,
        temperature=settings.ai.temperature,
        groq_api_key=settings.ai.groq_api_key,
        max_tokens=settings.ai.max_tokens_response,
    )
    logger.info(f"LLM: Groq ({model})")
    return LLMWrapper(llm, "groq", model)


def _get_gemini() -> LLMWrapper:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "Instala langchain-google-genai: pip install langchain-google-genai"
        )

    model = settings.ai.llm_model or settings.ai.google_model
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=settings.ai.temperature,
        google_api_key=settings.ai.google_api_key,
        max_output_tokens=settings.ai.max_tokens_response,
    )
    logger.info(f"LLM: Gemini ({model})")
    return LLMWrapper(llm, "gemini", model)


def _get_ollama() -> LLMWrapper:
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError("Instala langchain-ollama: pip install langchain-ollama")

    model = settings.ai.llm_model or settings.ai.ollama_model
    llm = ChatOllama(
        model=model,
        temperature=settings.ai.temperature,
        base_url=settings.ai.ollama_base_url,
    )
    logger.info(f"LLM: Ollama ({model}) - Local")
    return LLMWrapper(llm, "ollama", model)


PROVIDERS = {
    "deepseek": _get_deepseek,
    "openai": _get_openai,
    "claude": _get_claude,
    "groq": _get_groq,
    "gemini": _get_gemini,
    "ollama": _get_ollama,
}


@lru_cache(maxsize=1)
def get_llm(provider: str = None) -> LLMWrapper:
    """Retorna el LLM configurado según el proveedor"""
    provider = provider or settings.ai.llm_provider

    if provider not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Proveedor '{provider}' no soportado. Usa: {available}")

    try:
        return PROVIDERS[provider]()
    except Exception as e:
        logger.error(f"Error inicializando {provider}: {e}")
        raise


# Alias para compatibilidad
def get_available_llm() -> LLMWrapper:
    return get_llm()
