import logging
import sys
from config.settings import settings

def setup_logging():
    """Configura el logging para toda la aplicación"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.logs.level)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.logs.level)
    formatter = logging.Formatter(settings.logs.format)
    console_handler.setFormatter(formatter)

    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    
    # Silenciar logs innecesarios
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"✅ Logging configurado - Nivel: {settings.logs.level}")
    logging.info("🤖 Sistema 100% LLM-driven operativo")