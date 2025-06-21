import argparse
import logging
from utils.logging_config import setup_logging
from sql.pipeline_ejecucion import full_pipeline

setup_logging()
logger = logging.getLogger(__name__)

def parse_args():
    """Parsea argumentos de la línea de comandos"""
    parser = argparse.ArgumentParser(
        description="RAG-SQL: Convierte consultas en lenguaje natural a SQL"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Consulta en lenguaje natural para procesar"
    )
    return parser.parse_args()

def main():
    """Función principal de la aplicación"""
    args = parse_args()
    
    query = args.query if args.query else input("Ingresa tu consulta: ")
    
    logger.info(f"Procesando consulta: '{query}'")
    try:
        respuesta = full_pipeline(query)
        print("\n=== RESPUESTA ===")
        print(respuesta)
    except Exception as e:
        logger.exception("Error al procesar consulta")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()