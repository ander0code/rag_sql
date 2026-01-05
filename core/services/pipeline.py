# Pipeline - Orquestador principal del flujo RAG-SQL

import time
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from core.ports.llm_port import LLMPort
from core.ports.semantic_cache_port import SemanticCachePort
from core.services.schema_scanner import SchemaScanner
from core.services.schema_retriever import SchemaRetriever
from core.services.security import is_safe_sql

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "schemas"
CACHE_FILE = CACHE_DIR / "discovered_schemas.json"
MAX_RETRIES = 4


class Pipeline:
    """
    Orquestador principal del flujo RAG-SQL.
    Recibe todas las dependencias por constructor (Dependency Injection).

    Flujo:
    1. QueryEnhancer - Mejora la query del usuario
    2. AmbiguityDetector - Detecta si falta información
    3. SemanticCache - Busca respuestas similares
    4. SchemaRetriever - Selecciona tablas relevantes
    5. SQLGenerator - Genera SQL
    6. SQLValidator - Valida seguridad
    7. QueryExecutor - Ejecuta en DB
    8. ResponseGenerator - Genera respuesta natural
    """

    def __init__(
        self,
        llm: LLMPort,
        executor,  # QueryExecutor
        sql_gen,  # SQLGenerator
        response_gen,  # ResponseGenerator
        query_rewriter,  # QueryRewriter
        query_enhancer,  # QueryEnhancer
        ambiguity_detector,  # AmbiguityDetector
        clarify_agent,  # ClarifyAgent
        context_summarizer,  # ContextSummarizer
        semantic_cache: SemanticCachePort,
        db_uri: str,
        use_cache: bool = True,
    ):
        start = time.time()

        # Dependencias inyectadas
        self.llm = llm
        self.executor = executor
        self.sql_gen = sql_gen
        self.response_gen = response_gen
        self.query_rewriter = query_rewriter
        self.query_enhancer = query_enhancer
        self.ambiguity_detector = ambiguity_detector
        self.clarify_agent = clarify_agent
        self.context_summarizer = context_summarizer
        self.semantic_cache = semantic_cache
        self.db_uri = db_uri

        # Schema
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

    def _scan_db(self):
        """Escanea la base de datos y guarda el schema"""
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

    def _build_schema_summary(self):
        """Configura agentes con metadata del schema"""
        if not self.retriever:
            return

        tables_metadata = []
        for schema in self.retriever.schemas:
            meta = schema.get("metadata", {})
            if meta.get("table_name") and not meta["table_name"].startswith("_"):
                tables_metadata.append(meta)

        self.ambiguity_detector.set_schema_info(tables_metadata)
        self.clarify_agent.set_retriever(self.retriever)

    def check_ambiguity(
        self, query: str, context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Verifica si la query es ambigua y retorna opciones de clarificación."""
        is_ambiguous, entity_type, question = self.ambiguity_detector.check(
            query, context
        )

        if not is_ambiguous:
            return None

        options = self.clarify_agent.get_options_for_entity(entity_type)
        return self.clarify_agent.build_clarification_response(
            question, entity_type, options
        )

    def run(
        self,
        query: str,
        schema: Optional[str] = None,
        context: str = "",
        skip_enhancement: bool = False,
    ) -> Tuple[str, Optional[int]]:
        """
        Ejecuta el flujo completo.

        Args:
            query: Consulta del usuario
            schema: Schema de DB (opcional si solo hay uno)
            context: Contexto de conversación anterior
            skip_enhancement: Saltar mejora de query

        Returns:
            (respuesta, tokens_usados)
        """
        total_start = time.time()
        tokens_used = 0

        if not self.retriever or not self.retriever.schemas:
            return "Error: No hay schemas. Ejecuta: python main.py --scan", None

        # Resolver schema
        if not schema:
            if len(self._available_schemas) == 1:
                schema = self._available_schemas[0]
            else:
                return (
                    f"Especifica schema. Disponibles: {', '.join(self._available_schemas)}",
                    None,
                )

        # 1. Mejorar query
        if not skip_enhancement:
            enhanced_query = self.query_enhancer.enhance(query, context)
            if enhanced_query != query:
                logger.info(f"Query mejorada: '{query}' → '{enhanced_query}'")
            query = enhanced_query

        # 2. Reescribir para normalizar
        original_query = query
        query = self.query_rewriter.rewrite(query)

        # 3. Verificar cache semántico
        if self.semantic_cache.is_available():
            semantic_hit = self.semantic_cache.search(query)
            if semantic_hit:
                logger.info(f"Semantic Cache HIT (score: {semantic_hit['score']:.3f})")
                return semantic_hit["result"], 0

        logger.info(f"Query: '{query}'")

        # 4. Recuperar tablas relevantes
        relevant = self.retriever.get_relevant(query, target_schema=schema)
        if not relevant:
            return "Error: No se encontraron tablas relevantes.", None

        # 5. Generar y ejecutar SQL con retry
        result = None
        last_error = None
        sql = None

        for attempt in range(MAX_RETRIES):
            sql = self.sql_gen.generate(
                query, relevant, schema, previous_error=last_error
            )

            if not is_safe_sql(sql):
                return "Error: SQL no seguro.", None

            result = self.executor.execute(sql)

            if "error" not in result:
                break
            else:
                last_error = result["error"]
                logger.warning(f"Retry {attempt + 1}: {last_error[:80]}")

                if attempt == MAX_RETRIES - 1:
                    return f"Error SQL: {last_error}", tokens_used

        # 6. Generar respuesta natural
        response = self.response_gen.generate(original_query, result)

        # 7. Guardar en cache semántico
        if self.semantic_cache.is_available():
            tables_used = [s["metadata"]["table_name"] for s in relevant]
            self.semantic_cache.save(query, sql, response, tables_used)

        total_time = time.time() - total_start
        logger.info(f"Total: {total_time:.1f}s")

        return response, tokens_used

    def get_optimized_context(self, messages: list) -> str:
        """Obtiene contexto optimizado de una conversación."""
        if not messages:
            return ""

        if len(messages) > 6:
            return self.context_summarizer.get_context_with_summary(
                messages, keep_recent=4
            )

        return "\n".join(
            [
                f"{'Usuario' if m.get('role') == 'user' else 'Asistente'}: {m.get('content', '')[:200]}"
                for m in messages
            ]
        )

    def get_info(self) -> dict:
        """Retorna info de schemas disponibles"""
        return {
            "schemas": self._available_schemas,
            "total_tables": len(self.retriever.schemas) if self.retriever else 0,
            "single_schema": len(self._available_schemas) == 1,
        }
