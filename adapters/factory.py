# Fábrica - Crea el Pipeline con todas las dependencias inyectadas

from typing import Optional

from config.settings import settings
from adapters.outbound.llm.llm_factory import get_available_llm
from adapters.outbound.database.postgresql import PostgreSQLAdapter
from adapters.outbound.cache.redis_cache import get_redis_client
from adapters.outbound.cache.qdrant_cache import get_semantic_cache

from core.services.pipeline import Pipeline
from core.services.sql import SQLGenerator, QueryExecutor
from core.services.response import ResponseGenerator
from core.services.query import (
    QueryRewriter,
    QueryEnhancer,
    AmbiguityDetector,
    ClarifyAgent,
)
from core.services.context import ContextSummarizer


class DependencyContainer:
    """Contenedor de dependencias. Crea e inyecta todas las dependencias concretas."""

    def __init__(self, db_uri: Optional[str] = None):
        self.db_uri = db_uri or settings.db.db_uri
        self._llm = None
        self._db = None
        self._cache = None
        self._semantic_cache = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_available_llm()
        return self._llm

    @property
    def db(self):
        if self._db is None:
            self._db = PostgreSQLAdapter(self.db_uri)
        return self._db

    @property
    def cache(self):
        if self._cache is None:
            self._cache = get_redis_client()
        return self._cache

    @property
    def semantic_cache(self):
        if self._semantic_cache is None:
            self._semantic_cache = get_semantic_cache()
        return self._semantic_cache


def create_pipeline(db_uri: Optional[str] = None, use_cache: bool = True) -> Pipeline:
    """Factory function que crea el Pipeline con todas las dependencias."""
    container = DependencyContainer(db_uri)

    executor = QueryExecutor(container.db_uri)
    sql_gen = SQLGenerator(container.llm)
    response_gen = ResponseGenerator(container.llm)
    query_rewriter = QueryRewriter(container.llm)
    query_enhancer = QueryEnhancer(container.llm)
    ambiguity_detector = AmbiguityDetector(container.llm)
    clarify_agent = ClarifyAgent(executor)
    context_summarizer = ContextSummarizer(container.llm)

    return Pipeline(
        llm=container.llm,
        executor=executor,
        sql_gen=sql_gen,
        response_gen=response_gen,
        query_rewriter=query_rewriter,
        query_enhancer=query_enhancer,
        ambiguity_detector=ambiguity_detector,
        clarify_agent=clarify_agent,
        context_summarizer=context_summarizer,
        semantic_cache=container.semantic_cache,
        db_uri=container.db_uri,
        use_cache=use_cache,
    )


_pipeline: Optional[Pipeline] = None


def get_pipeline() -> Pipeline:
    """Obtiene instancia singleton del Pipeline"""
    global _pipeline
    if _pipeline is None:
        _pipeline = create_pipeline()
    return _pipeline
