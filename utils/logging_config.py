import logging
import sys
from config.settings import settings

def setup_logging():
    """Configura el logging para toda la aplicación"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.logs.level)
    
    # Formatter SIN truncamiento
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.logs.level)
    console_handler.setFormatter(formatter)
    
    # NUEVO: Permitir mensajes largos
    console_handler.terminator = '\n'

    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    
    # Silenciar logs innecesarios pero mantener SQL visible
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"✅ Logging configurado - Nivel: {settings.logs.level}")
    logging.info("🤖 Sistema 100% LLM-driven operativo")