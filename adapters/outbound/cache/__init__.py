# Adaptadores de caché
from adapters.outbound.cache.redis_cache import RedisClient, get_redis_client

__all__ = ["RedisClient", "get_redis_client"]
