import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from config.settings import settings

logger = logging.getLogger(__name__)

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

def get_available_llm() -> ChatOpenAI:
    """
    Obtiene el modelo LLM disponible con fallback automático.
    Intenta Deepseek primero, luego OpenAI si falla.
    """
    logger.info("Intentando inicializar LLM con fallback automático...")
    logger.info(f"Deepseek API Key disponible: {bool(settings.ai.deepseek_api_key and len(settings.ai.deepseek_api_key) > 10)}")
    logger.info(f"OpenAI API Key disponible: {bool(settings.ai.openai_api_key and len(settings.ai.openai_api_key) > 10)}")
    
    # Intentar con Deepseek primero
    if settings.ai.deepseek_api_key and settings.ai.deepseek_api_key.startswith('sk-'):
        try:
            logger.info("Probando conexión con Deepseek...")
            deepseek_llm = get_deepseek_llm()
            
            # Hacer una prueba rápida
            test_response = deepseek_llm.invoke([HumanMessage(content="Hola")])
            if test_response and test_response.content:
                logger.info("✅ Deepseek conectado exitosamente")
                return deepseek_llm
        except Exception as e:
            logger.warning(f"❌ Deepseek falló: {str(e)[:100]}...")
    
    # Fallback a OpenAI
    if settings.ai.openai_api_key and settings.ai.openai_api_key.startswith('sk-'):
        try:
            logger.info("Probando conexión con OpenAI como fallback...")
            openai_llm = get_openai_llm()
            
            # Hacer una prueba rápida
            test_response = openai_llm.invoke([HumanMessage(content="Hola")])
            if test_response and test_response.content:
                logger.info("✅ OpenAI conectado exitosamente")
                return openai_llm
        except Exception as e:
            logger.error(f"❌ OpenAI también falló: {str(e)[:100]}...")
    
    raise Exception("❌ No hay modelos LLM disponibles. Verifica tus API keys en el archivo .env")