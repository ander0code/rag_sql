# Rate limiter: controla requests por IP usando Redis

import time
import logging
from typing import Tuple
from infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT = 60
DEFAULT_WINDOW = 60
RATE_KEY_PREFIX = "rate:"


# Limita requests por cliente usando sliding window
class RateLimiter:
    def __init__(self, limit: int = DEFAULT_RATE_LIMIT, window: int = DEFAULT_WINDOW):
        self.redis = get_redis_client()
        self.limit = limit
        self.window = window

    def _key(self, identifier: str) -> str:
        return f"{RATE_KEY_PREFIX}{identifier}"

    # Verifica si el cliente puede hacer request
    def check(self, identifier: str) -> Tuple[bool, int, int]:
        if not self.redis.is_connected():
            return True, self.limit, 0

        key = self._key(identifier)
        current_time = int(time.time())
        window_start = current_time - self.window

        try:
            data = self.redis.get(key)

            if not data:
                self.redis.set(key, {"count": 1, "start": current_time}, self.window)
                return True, self.limit - 1, 0

            count = data.get("count", 0)
            start = data.get("start", current_time)

            if start < window_start:
                self.redis.set(key, {"count": 1, "start": current_time}, self.window)
                return True, self.limit - 1, 0

            if count >= self.limit:
                retry_after = self.window - (current_time - start)
                logger.warning(f"Rate limit alcanzado: {identifier}")
                return False, 0, max(0, retry_after)

            data["count"] = count + 1
            remaining_ttl = self.window - (current_time - start)
            self.redis.set(key, data, max(1, remaining_ttl))

            return True, self.limit - count - 1, 0

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True, self.limit, 0


_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
