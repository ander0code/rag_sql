import time
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from infrastructure.llm.clients import get_available_llm
from infrastructure.config.settings import settings
from infrastructure.cache.query_cache import get_query_cache
from core.discovery.schema_scanner import SchemaScanner
from core.retrieval.schema_retriever import SchemaRetriever
from core.generation.sql_generator import SQLGenerator
from core.generation.response_generator import ResponseGenerator
from core.generation.query_rewriter import QueryRewriter
from core.execution.query_executor import QueryExecutor
from core.execution.validator import is_safe_sql
from core.agents.ambiguity_detector import AmbiguityDetector
from core.agents.clarify_agent import ClarifyAgent
from infrastructure.cache.semantic_cache import get_semantic_cache
from core.execution.sql_optimizer import optimize_sql
from utils.logging import token_counter

logger = logging.getLogger(__name__)

CACHE_FILE = (
    Path(__file__).parent.parent
    / "infrastructure"
    / "config"
    / "schemas"
    / "discovered_schemas.json"
)
MAX_RETRIES = 4


# Orquestador principal del flujo RAG-SQL
class Pipeline:
    # Inicializa componentes y carga schema desde cache o escanea DB
    def __init__(self, db_uri: Optional[str] = None, use_cache: bool = True):
        start = time.time()
        self.db_uri = db_uri or settings.db.db_uri
        self.llm = get_available_llm()
        self.executor = QueryExecutor(self.db_uri)
        self.sql_gen = SQLGenerator(self.llm)
        self.response_gen = ResponseGenerator(self.llm)
        self.query_rewriter = QueryRewriter(self.llm)
        self.ambiguity_detector = AmbiguityDetector(self.llm)
        self.clarify_agent = ClarifyAgent(self.executor)
        self.query_cache = get_query_cache()
        self.semantic_cache = get_semantic_cache()
        self.retriever = None
        self._available_schemas = []

        if use_cache and CACHE_FILE.exists():
            self.retriever = SchemaRetriever.from_file(self.llm)
            self._available_schemas = self.retriever.get_available_schemas()
            self._build_schema_summary()
            logger.info(
                f"Cache: {len(self.retriever.schemas)} tablas ({time.time() - start:.1f}s)"
            )
        else:
            self._scan_db()

    # Escanea la base de datos y guarda el schema
    def _scan_db(self):
        start = time.time()
        scanner = SchemaScanner(self.db_uri)
        scanner.scan()
        scanner.save()
        self.retriever = SchemaRetriever.from_scanner(self.llm, scanner)
        self._available_schemas = self.retriever.get_available_schemas()
        self._build_schema_summary()
        logger.info(
            f"Escaneado: {len(self.retriever.schemas)} tablas ({time.time() - start:.1f}s)"
        )

    # Configura agentes con metadata del schema descubierto
    def _build_schema_summary(self):
        if not self.retriever:
            return

        tables_metadata = []
        for schema in self.retriever.schemas:
            meta = schema.get("metadata", {})
            if meta.get("table_name") and not meta["table_name"].startswith("_"):
                tables_metadata.append(meta)

        self.ambiguity_detector.set_schema_info(tables_metadata)
        self.clarify_agent.set_retriever(self.retriever)

    # Verifica si la query es ambigua y retorna opciones de clarificación
    def check_ambiguity(
        self, query: str, context: str = ""
    ) -> Optional[Dict[str, Any]]:
        is_ambiguous, entity_type, question = self.ambiguity_detector.check(
            query, context
        )

        if not is_ambiguous:
            return None

        options = self.clarify_agent.get_options(entity_type)
        return self.clarify_agent.build_clarification_response(
            question, entity_type, options
        )

    # Ejecuta el flujo completo: cache -> rewrite -> SQL -> execute -> response
    def run(
        self, query: str, schema: Optional[str] = None, context: str = ""
    ) -> Tuple[str, Optional[int]]:
        total_start = time.time()
        token_counter.reset()

        if not self.retriever or not self.retriever.schemas:
            return "Error: No hay schemas. Ejecuta: python main.py --scan", None

        if not schema:
            if len(self._available_schemas) == 1:
                schema = self._available_schemas[0]
            else:
                return (
                    f"Especifica schema. Disponibles: {', '.join(self._available_schemas)}",
                    None,
                )

        # Verificar cache semántico
        semantic_hit = self.semantic_cache.search(query)
        if semantic_hit:
            logger.info(f"Semantic Cache HIT (score: {semantic_hit['score']:.3f})")
            return semantic_hit["result"], 0

        # Verificar cache exacto
        cached = self.query_cache.get(query, schema)
        if cached:
            logger.info(f"Cache HIT ({time.time() - total_start:.2f}s)")
            return cached[0], cached[1]

        # Reescribir query
        t0 = time.time()
        original_query = query
        query = self.query_rewriter.rewrite(query)
        if query != original_query and settings.debug:
            logger.debug(f"Reescrita ({time.time() - t0:.1f}s)")

        logger.info(f"Query: '{query}'")

        # Recuperar tablas relevantes
        t0 = time.time()
        relevant = self.retriever.get_relevant(query, target_schema=schema)
        if not relevant:
            return "Error: No se encontraron tablas relevantes.", None

        if settings.debug:
            logger.debug(
                f"Tablas: {[s['metadata']['table_name'] for s in relevant]} ({time.time() - t0:.1f}s)"
            )

        # Generar y ejecutar SQL con retry
        result = None
        last_error = None

        for attempt in range(MAX_RETRIES):
            t0 = time.time()
            sql = self.sql_gen.generate(
                query, relevant, schema, previous_error=last_error
            )

            sql = optimize_sql(sql)

            if settings.debug:
                logger.debug(f"SQL ({attempt + 1}): {sql} ({time.time() - t0:.1f}s)")

            if not is_safe_sql(sql):
                return "Error: SQL no seguro.", None

            t0 = time.time()
            result = self.executor.execute(sql)

            if "error" not in result:
                if settings.debug:
                    logger.debug(
                        f"Ejecutado: {len(result.get('data', []))} filas ({time.time() - t0:.1f}s)"
                    )
                break
            else:
                last_error = result["error"]
                logger.warning(f"Retry {attempt + 1}: {last_error[:80]}")

                if attempt == MAX_RETRIES - 1:
                    return f"Error SQL: {last_error}", token_counter.total_tokens

        # Generar respuesta natural
        t0 = time.time()
        response = self.response_gen.generate(original_query, result)

        if settings.debug:
            logger.debug(f"Respuesta ({time.time() - t0:.1f}s)")

        # Guardar en caches
        self.query_cache.set(
            original_query, schema, response, token_counter.total_tokens
        )
        tables_used = [s["metadata"]["table_name"] for s in relevant]
        self.semantic_cache.save(query, sql, response, tables_used)

        total_time = time.time() - total_start
        logger.info(f"Total: {total_time:.1f}s | Tokens: {token_counter.total_tokens}")

        return response, token_counter.total_tokens

    # Retorna info de schemas disponibles
    def get_info(self) -> dict:
        return {
            "schemas": self._available_schemas,
            "total_tables": len(self.retriever.schemas) if self.retriever else 0,
            "single_schema": len(self._available_schemas) == 1,
        }


_pipeline = None


# Wrapper para ejecutar pipeline desde CLI
def run_pipeline(query: str, schema: Optional[str] = None) -> Tuple[str, Optional[int]]:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline.run(query, schema)


# Wrapper para obtener info de DB desde CLI
def get_db_info() -> dict:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline.get_info()
