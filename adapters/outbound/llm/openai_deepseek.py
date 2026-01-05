# Clientes LLM con tracking de tokens

import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from config.settings import settings
from utils.logging import token_counter

logger = logging.getLogger(__name__)


# Wrapper de LLM con conteo de tokens
class LLMWrapper:
    def __init__(self, llm, model_name: str):
        self.llm = llm
        self.model_name = model_name

    def invoke(self, messages: list):
        input_text = " ".join(m.content for m in messages if hasattr(m, "content"))

        response = self.llm.invoke(messages)

        output_text = (
            response.content if hasattr(response, "content") else str(response)
        )
        token_counter.track(input_text, output_text, self.model_name)

        return response


@lru_cache(maxsize=1)
def get_openai_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.ai.openai_model,
        temperature=settings.ai.temperature,
        openai_api_key=settings.ai.openai_api_key,
    )


@lru_cache(maxsize=1)
def get_deepseek_llm() -> ChatOpenAI:
    return ChatOpenAI(
        temperature=settings.ai.temperature,
        model=settings.ai.deepseek_model,
        base_url="https://api.deepseek.com/v1",
        api_key=settings.ai.deepseek_api_key,
    )


# Retorna el primer LLM disponible (Deepseek > OpenAI)
def get_available_llm() -> LLMWrapper:
    if settings.ai.deepseek_api_key and settings.ai.deepseek_api_key.startswith("sk-"):
        try:
            llm = get_deepseek_llm()
            llm.invoke([HumanMessage(content="test")])
            logger.info("Deepseek conectado")
            return LLMWrapper(llm, "deepseek")
        except Exception as e:
            logger.warning(f"Deepseek falló: {str(e)[:50]}")

    if settings.ai.openai_api_key and settings.ai.openai_api_key.startswith("sk-"):
        try:
            llm = get_openai_llm()
            llm.invoke([HumanMessage(content="test")])
            logger.info("OpenAI conectado")
            return LLMWrapper(llm, "gpt-4o-mini")
        except Exception as e:
            logger.error(f"OpenAI falló: {str(e)[:50]}")

    raise Exception("No hay LLM disponible")
