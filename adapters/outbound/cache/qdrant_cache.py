# Cache semántico usando Qdrant para queries similares

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.ports.semantic_cache_port import SemanticCachePort

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sql_query_cache"
SIMILARITY_THRESHOLD = 0.95
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_SIZE = 384


class SemanticCache(SemanticCachePort):
    """Implementación de SemanticCachePort usando Qdrant"""

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.qdrant_url = qdrant_url
        self._client = None
        self._embedder = None
        self._initialized = False

    def _init_client(self):
        if self._initialized:
            return True

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            self._client = QdrantClient(url=self.qdrant_url)

            collections = self._client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)

            if not exists:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE, distance=Distance.COSINE
                    ),
                )
                logger.info(f"Colección Qdrant '{COLLECTION_NAME}' creada")

            self._initialized = True
            logger.info("Semantic Cache conectado a Qdrant")
            return True

        except Exception as e:
            logger.warning(f"Semantic Cache no disponible: {e}")
            return False

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(EMBEDDING_MODEL)
                logger.info(f"Modelo embeddings cargado: {EMBEDDING_MODEL}")
            except Exception as e:
                logger.warning(f"Error cargando embedder: {e}")
                return None
        return self._embedder

    def _embed(self, text: str) -> Optional[list]:
        embedder = self._get_embedder()
        if not embedder:
            return None

        try:
            return embedder.encode(text).tolist()
        except Exception as e:
            logger.warning(f"Error generando embedding: {e}")
            return None

    # Busca queries similares en cache
    def search(self, query: str) -> Optional[Dict[str, Any]]:
        if not self._init_client():
            return None

        vector = self._embed(query)
        if not vector:
            return None

        try:
            results = self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                limit=1,
                score_threshold=SIMILARITY_THRESHOLD,
            ).points

            if results and len(results) > 0:
                hit = results[0]
                logger.info(f"Semantic Cache HIT (score: {hit.score:.3f})")
                return {
                    "sql": hit.payload.get("sql"),
                    "result": hit.payload.get("result"),
                    "original_query": hit.payload.get("query"),
                    "score": hit.score,
                }

            return None

        except Exception as e:
            logger.warning(f"Error buscando en cache: {e}")
            return None

    # Guarda query y resultado en cache semántico
    def save(self, query: str, sql: str, result: str, tables_used: list = None) -> bool:
        if not self._init_client():
            return False

        vector = self._embed(query)
        if not vector:
            return False

        try:
            import uuid

            point_id = str(uuid.uuid4())

            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {
                            "query": query,
                            "sql": sql,
                            "result": result[:500],
                            "tables": tables_used or [],
                            "timestamp": datetime.now().isoformat(),
                            "hit_count": 0,
                        },
                    }
                ],
            )

            logger.debug(f"Semantic Cache SAVE: {query[:50]}...")
            return True

        except Exception as e:
            logger.warning(f"Error guardando en cache: {e}")
            return False

    def is_available(self) -> bool:
        """Verifica si el cache semántico está disponible"""
        return self._init_client()

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del cache"""
        if not self._init_client():
            return {"status": "disconnected"}

        try:
            info = self._client.get_collection(COLLECTION_NAME)
            return {
                "status": "connected",
                "points_count": info.points_count,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


_semantic_cache = None


def get_semantic_cache() -> SemanticCache:
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache
