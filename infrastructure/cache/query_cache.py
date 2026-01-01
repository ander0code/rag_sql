# Cache de queries exactas usando Redis

import hashlib
import logging
from typing import Optional, Tuple
from infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

CACHE_PREFIX = "query_cache:"
DEFAULT_TTL = 300


# Cache exacto de queries usando hash MD5
class QueryCache:
    def __init__(self, ttl: int = DEFAULT_TTL):
        self.redis = get_redis_client()
        self.ttl = ttl

    def _make_key(self, query: str, schema: str) -> str:
        normalized = query.lower().strip()
        content = f"{schema}:{normalized}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{CACHE_PREFIX}{hash_val}"

    # Busca una query en cache
    def get(self, query: str, schema: str) -> Optional[Tuple[str, int]]:
        if not self.redis.is_connected():
            return None

        key = self._make_key(query, schema)
        data = self.redis.get(key)

        if data:
            logger.debug(f"Cache HIT: {query[:30]}...")
            return data.get("result"), data.get("tokens", 0)

        return None

    # Guarda una query en cache
    def set(self, query: str, schema: str, result: str, tokens: int = 0):
        if not self.redis.is_connected():
            return

        key = self._make_key(query, schema)
        self.redis.set(key, {"result": result, "tokens": tokens}, self.ttl)
        logger.debug(f"Cache SET: {query[:30]}...")

    # Invalida una entrada del cache
    def invalidate(self, query: str, schema: str):
        if not self.redis.is_connected():
            return

        key = self._make_key(query, schema)
        self.redis.delete(key)


_query_cache = None


def get_query_cache(ttl: int = DEFAULT_TTL) -> QueryCache:
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache(ttl)
    return _query_cache
