import logging
import sys
from config.settings import settings

def setup_logging():
    """Configura el logging para toda la aplicación SIN TRUNCAMIENTO"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.logs.level)
    
    # Formatter SIN truncamiento - COMPLETAMENTE SIN LÍMITES
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.logs.level)
    console_handler.setFormatter(formatter)
    
    # NUEVO: Configuración para mensajes largos SIN LÍMITES
    console_handler.terminator = '\n'
    
    # CRÍTICO: Remover cualquier limitación de buffer
    sys.stdout.reconfigure(line_buffering=False)

    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    
    # Silenciar logs innecesarios pero mantener SQL completamente visible
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # NUEVO: Configurar logger específico para SQL sin límites
    sql_logger = logging.getLogger("sql")
    sql_logger.setLevel(logging.DEBUG)
    
    logging.info(f"✅ Logging configurado - Nivel: {settings.logs.level}")
    logging.info("🤖 Sistema 100% LLM-driven operativo")
    logging.info("🔧 Logging SQL: SIN TRUNCAMIENTO activado")