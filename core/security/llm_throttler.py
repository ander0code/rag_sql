# LLM throttler: controla requests concurrentes al LLM

import asyncio
import logging
import time
from infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

MAX_CONCURRENT_LLM = 5
WAIT_TIMEOUT = 60
REDIS_THROTTLE_KEY = "llm:active_requests"


# Limita requests concurrentes al LLM usando Redis
class LLMThrottler:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_LLM):
        self.max_concurrent = max_concurrent
        self.redis = get_redis_client()
        self._local_semaphore = asyncio.Semaphore(max_concurrent)
        self._use_redis = self.redis.is_connected()

        if self._use_redis:
            if self.redis.get(REDIS_THROTTLE_KEY) is None:
                self.redis.set(REDIS_THROTTLE_KEY, {"count": 0}, ttl=3600)

    # Adquiere slot para hacer request al LLM
    async def acquire(self, timeout: float = WAIT_TIMEOUT) -> bool:
        start_time = time.time()

        while True:
            if self._try_acquire():
                return True

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Timeout esperando slot LLM ({timeout}s)")
                return False

            await asyncio.sleep(0.5)

    def _try_acquire(self) -> bool:
        if self._use_redis:
            return self._redis_acquire()
        else:
            return self._local_semaphore.locked() is False

    def _redis_acquire(self) -> bool:
        try:
            data = self.redis.get(REDIS_THROTTLE_KEY)
            if data is None:
                data = {"count": 0}

            current = data.get("count", 0)

            if current < self.max_concurrent:
                data["count"] = current + 1
                self.redis.set(REDIS_THROTTLE_KEY, data, ttl=3600)
                logger.debug(
                    f"Slot LLM adquirido ({current + 1}/{self.max_concurrent})"
                )
                return True

            logger.debug(f"Esperando slot LLM ({current}/{self.max_concurrent})")
            return False

        except Exception as e:
            logger.error(f"Error en throttler: {e}")
            return True

    # Libera slot después de completar request
    def release(self):
        if self._use_redis:
            self._redis_release()

    def _redis_release(self):
        try:
            data = self.redis.get(REDIS_THROTTLE_KEY)
            if data is None:
                return

            current = data.get("count", 0)
            data["count"] = max(0, current - 1)
            self.redis.set(REDIS_THROTTLE_KEY, data, ttl=3600)
            logger.debug(f"Slot LLM liberado ({data['count']}/{self.max_concurrent})")

        except Exception as e:
            logger.error(f"Error liberando slot: {e}")

    # Retorna estado actual del throttler
    def get_status(self) -> dict:
        if self._use_redis:
            data = self.redis.get(REDIS_THROTTLE_KEY)
            current = data.get("count", 0) if data else 0
        else:
            current = self.max_concurrent - self._local_semaphore._value

        return {
            "active_requests": current,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - current,
            "using_redis": self._use_redis,
        }


_throttler = None


def get_llm_throttler() -> LLMThrottler:
    global _throttler
    if _throttler is None:
        _throttler = LLMThrottler()
    return _throttler
