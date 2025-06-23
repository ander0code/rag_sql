import argparse
import logging
from utils.logging_config import setup_logging
from sql.pipeline_ejecucion import full_pipeline

setup_logging()
logger = logging.getLogger(__name__)

def parse_args():
    """Parsea argumentos de la línea de comandos"""
    parser = argparse.ArgumentParser(
        description="RAG-SQL: Convierte consultas en lenguaje natural a SQL para gestión de voluntarios"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Consulta en lenguaje natural para procesar"
    )
    parser.add_argument(
        "--schema", "-s",
        type=str,
        help="Schema de base de datos a consultar (ej: public, tenant_001, etc.)"
    )
    return parser.parse_args()

def main():
    """Función principal de la aplicación"""
    args = parse_args()
    
    # Solicitar query si no se proporciona
    query = args.query if args.query else input("Ingresa tu consulta: ")
    
    # Solicitar schema si no se proporciona
    schema = args.schema
    if not schema:
        print("\n--- Configuración de Schema ---")
        print("El sistema necesita saber en qué schema buscar las tablas.")
        print("Ejemplos comunes: public, tenant_001, org_123, etc.")
        schema = input("Ingresa el schema a consultar (Enter para 'public'): ").strip()
        if not schema:
            schema = "public"
    
    logger.info(f"Procesando consulta: '{query}' en schema: '{schema}'")
    try:
        respuesta = full_pipeline(query, schema)
        print("\n=== RESPUESTA ===")
        print(respuesta)
    except Exception as e:
        logger.exception("Error al procesar consulta")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()