"""RAG-SQL Dinámico."""

import sys
import logging
import argparse


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="RAG-SQL Dinámico")
    parser.add_argument("--query", "-q", help="Consulta en lenguaje natural")
    parser.add_argument("--schema", "-s", help="Schema (opcional si DB tiene uno solo)")
    parser.add_argument("--info", action="store_true", help="Muestra info de la DB")
    parser.add_argument("--scan", action="store_true", help="Re-escanea la DB")
    args = parser.parse_args()
    
    setup_logging()
    
    from application.pipeline import Pipeline, run_pipeline, get_db_info
    
    # Modo info
    if args.info:
        info = get_db_info()
        print(f"\n📊 Base de Datos:")
        print(f"   Schemas: {', '.join(info['schemas'])}")
        print(f"   Tablas: {info['total_tables']}")
        print(f"   Auto-schema: {'Sí' if info['single_schema'] else 'No (especificar --schema)'}")
        return
    
    # Modo scan
    if args.scan:
        from core.discovery.schema_scanner import SchemaScanner
        from infrastructure.config.settings import settings
        
        scanner = SchemaScanner(settings.db.db_uri)
        scanner.scan()
        scanner.save()
        print(f"\n✅ DB escaneada: {scanner.get_info()}")
        return
    
    # Modo query
    query = args.query or input("Consulta: ").strip()
    if not query:
        print("Error: Query requerida")
        return
    
    try:
        response = run_pipeline(query, args.schema)
        print(f"\n{'='*50}")
        print(f"📝 {query}")
        print(f"{'='*50}")
        print(response)
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    main()