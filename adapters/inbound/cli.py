# CLI Adapter - Entry point por línea de comandos

import sys
import logging
import argparse
from adapters.factory import get_pipeline
from core.services.schema_scanner import SchemaScanner
from config.settings import settings


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="RAG-SQL - Natural Language to SQL")
    parser.add_argument("--query", "-q", help="Consulta en lenguaje natural")
    parser.add_argument("--schema", "-s", help="Schema (opcional si DB tiene uno solo)")
    parser.add_argument("--info", action="store_true", help="Muestra info de la DB")
    parser.add_argument("--scan", action="store_true", help="Re-escanea la DB")
    args = parser.parse_args()

    setup_logging()

    # Modo info
    if args.info:
        pipeline = get_pipeline()
        info = pipeline.get_info()
        print("\nBase de Datos:")
        print(f"   Schemas: {', '.join(info['schemas'])}")
        print(f"   Tablas: {info['total_tables']}")
        print(
            f"   Auto-schema: {'Sí' if info['single_schema'] else 'No (especificar --schema)'}"
        )
        return

    # Modo scan
    if args.scan:
        scanner = SchemaScanner(settings.db.db_uri)
        scanner.scan()
        scanner.save()
        print(f"\nDB escaneada: {scanner.get_info()}")
        return

    # Modo query
    query = args.query or input("Consulta: ").strip()
    if not query:
        print("Error: Query requerida")
        return

    try:
        pipeline = get_pipeline()
        response, tokens = pipeline.run(query, args.schema)
        print(f"\n{'=' * 50}")
        print(f"Query: {query}")
        print(f"{'=' * 50}")
        print(response)
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    main()
