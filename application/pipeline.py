"""Pipeline dinámico con cache y timers."""

import time
import logging
from pathlib import Path
from typing import Optional
from infrastructure.llm.clients import get_available_llm
from infrastructure.config.settings import settings
from core.discovery.schema_scanner import SchemaScanner
from core.retrieval.schema_retriever import SchemaRetriever
from core.generation.sql_generator import SQLGenerator
from core.generation.response_generator import ResponseGenerator
from core.execution.query_executor import QueryExecutor
from core.execution.validator import is_safe_sql

logger = logging.getLogger(__name__)

CACHE_FILE = (
    Path(__file__).parent.parent
    / "infrastructure"
    / "config"
    / "schemas"
    / "discovered_schemas.json"
)


class Pipeline:
    def __init__(self, db_uri: Optional[str] = None, use_cache: bool = True):
        start = time.time()
        self.db_uri = db_uri or settings.db.db_uri
        self.llm = get_available_llm()
        self.executor = QueryExecutor(self.db_uri)
        self.sql_gen = SQLGenerator(self.llm)
        self.response_gen = ResponseGenerator(self.llm)
        self.retriever = None
        self._available_schemas = []

        # Cargar desde cache si existe
        if use_cache and CACHE_FILE.exists():
            self.retriever = SchemaRetriever.from_file(self.llm)
            self._available_schemas = self.retriever.get_available_schemas()
            logger.info(
                f"✅ Cache cargado: {len(self.retriever.schemas)} tablas ({time.time() - start:.1f}s)"
            )
        else:
            self._scan_db()

    def _scan_db(self):
        start = time.time()
        scanner = SchemaScanner(self.db_uri)
        scanner.scan()
        scanner.save()
        self.retriever = SchemaRetriever.from_scanner(self.llm, scanner)
        self._available_schemas = self.retriever.get_available_schemas()
        logger.info(
            f"✅ DB escaneada: {len(self.retriever.schemas)} tablas ({time.time() - start:.1f}s)"
        )

    def run(self, query: str, schema: Optional[str] = None) -> str:
        total_start = time.time()

        if not self.retriever or not self.retriever.schemas:
            return "Error: No hay schemas. Ejecuta: python main.py --scan"

        # Auto-detectar schema
        if not schema:
            if len(self._available_schemas) == 1:
                schema = self._available_schemas[0]
            else:
                return f"Especifica --schema. Disponibles: {', '.join(self._available_schemas)}"

        logger.info(f"📝 Query: '{query}' en '{schema}'")

        # Recuperar tablas
        t0 = time.time()
        relevant = self.retriever.get_relevant(query, target_schema=schema)
        if not relevant:
            return "Error: No se encontraron tablas."
        logger.info(
            f"📋 Tablas: {[s['metadata']['table_name'] for s in relevant]} ({time.time() - t0:.1f}s)"
        )

        # Generar SQL
        t0 = time.time()
        sql = self.sql_gen.generate(query, relevant, schema)
        logger.info(f"SQL: {sql} ({time.time() - t0:.1f}s)")

        if not is_safe_sql(sql):
            return "Error: SQL no válido."

        # Ejecutar
        t0 = time.time()
        result = self.executor.execute(sql)
        if "error" in result:
            return f"Error: {result['error']}"
        logger.info(
            f"⚡ Ejecutado: {len(result.get('data', []))} filas ({time.time() - t0:.1f}s)"
        )

        # Respuesta
        t0 = time.time()
        response = self.response_gen.generate(query, result)
        logger.info(f"💬 Respuesta generada ({time.time() - t0:.1f}s)")

        logger.info(f"⏱️ Total: {time.time() - total_start:.1f}s")
        return response

    def get_info(self) -> dict:
        return {
            "schemas": self._available_schemas,
            "total_tables": len(self.retriever.schemas) if self.retriever else 0,
            "single_schema": len(self._available_schemas) == 1,
        }


_pipeline = None


def run_pipeline(query: str, schema: Optional[str] = None) -> str:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline.run(query, schema)


def get_db_info() -> dict:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline.get_info()
