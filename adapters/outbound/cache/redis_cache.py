# Cliente Redis wrapper con JSON serialization

import json
import logging
from typing import Optional
import redis
from config.settings import settings

logger = logging.getLogger(__name__)


# Wrapper de Redis con serialización JSON automática
class RedisClient:
    def __init__(self):
        self.client = None
        self.ttl = settings.session_ttl
        self._connect()

    def _connect(self):
        try:
            self.client = redis.from_url(settings.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Redis conectado")
        except Exception as e:
            logger.warning(f"Redis no disponible: {e}")
            self.client = None

    def get(self, key: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: dict, ttl: int = None):
        if not self.client:
            return
        try:
            self.client.setex(key, ttl or self.ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str):
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def is_connected(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False


_redis_client = None


def get_redis_client() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
