# Rate Limiter - Control de requests por IP/usuario

import time
import logging
from typing import Tuple, Optional
from adapters.outbound.cache import get_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Limita requests por IP/usuario usando sliding window.
    Usa Redis para storage distribuido.
    """

    def __init__(
        self, max_requests: int = 30, window_seconds: int = 60, prefix: str = "rl"
    ):
        self.redis = get_redis_client()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix
        self._enabled = self.redis.is_connected()

        if self._enabled:
            logger.info(f"RateLimiter: {max_requests} req/{window_seconds}s")
        else:
            logger.warning("RateLimiter deshabilitado (Redis no disponible)")

    def _key(self, identifier: str) -> str:
        """Genera clave única para el identifier"""
        return f"{self.prefix}:{identifier}"

    def check(self, identifier: str) -> Tuple[bool, int]:
        """
        Verifica si el identifier puede hacer request.

        Args:
            identifier: IP, user_id, o session_id

        Returns:
            (allowed, remaining): Si está permitido y cuántos quedan
        """
        if not self._enabled:
            return True, self.max_requests

        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # Obtener requests en la ventana actual
            data = self.redis.get(key) or {"requests": []}
            requests = data.get("requests", [])

            # Filtrar requests dentro de la ventana
            requests = [ts for ts in requests if ts > window_start]

            remaining = self.max_requests - len(requests)

            if remaining <= 0:
                logger.warning(f"Rate limit excedido: {identifier}")
                return False, 0

            # Agregar nueva request
            requests.append(now)
            self.redis.set(key, {"requests": requests}, ttl=self.window_seconds)

            return True, remaining - 1

        except Exception as e:
            logger.error(f"Error RateLimiter: {e}")
            return True, self.max_requests  # Fail open

    def get_remaining(self, identifier: str) -> int:
        """Retorna requests restantes sin consumir"""
        if not self._enabled:
            return self.max_requests

        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        try:
            data = self.redis.get(key) or {"requests": []}
            requests = [ts for ts in data.get("requests", []) if ts > window_start]
            return max(0, self.max_requests - len(requests))
        except Exception:
            return self.max_requests

    def reset(self, identifier: str):
        """Resetea el contador de un identifier"""
        if self._enabled:
            self.redis.delete(self._key(identifier))


class LLMThrottler:
    """
    Limita llamadas al LLM para:
    - No exceder rate limits de OpenAI/Deepseek
    - Controlar costos
    """

    def __init__(
        self, max_calls_per_minute: int = 60, max_tokens_per_minute: int = 100000
    ):
        self.redis = get_redis_client()
        self.max_calls = max_calls_per_minute
        self.max_tokens = max_tokens_per_minute
        self._enabled = self.redis.is_connected()

    def check_and_consume(self, estimated_tokens: int = 1000) -> Tuple[bool, str]:
        """
        Verifica si se puede hacer llamada al LLM.

        Returns:
            (allowed, reason): Si está permitido y por qué no
        """
        if not self._enabled:
            return True, ""

        now = time.time()
        window_start = now - 60
        key = "llm:throttle"

        try:
            data = self.redis.get(key) or {"calls": [], "tokens": 0}

            # Filtrar calls del último minuto
            calls = [c for c in data.get("calls", []) if c["ts"] > window_start]
            total_tokens = sum(c["tokens"] for c in calls)

            # Verificar límites
            if len(calls) >= self.max_calls:
                return False, f"Límite de {self.max_calls} calls/min alcanzado"

            if total_tokens + estimated_tokens > self.max_tokens:
                return False, f"Límite de {self.max_tokens} tokens/min alcanzado"

            # Registrar llamada
            calls.append({"ts": now, "tokens": estimated_tokens})
            self.redis.set(key, {"calls": calls}, ttl=60)

            return True, ""

        except Exception as e:
            logger.error(f"Error LLMThrottler: {e}")
            return True, ""  # Fail open


# SINGLETONS

_rate_limiter: Optional[RateLimiter] = None
_llm_throttler: Optional[LLMThrottler] = None


def get_rate_limiter() -> RateLimiter:
    """Obtiene instancia singleton del RateLimiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_llm_throttler() -> LLMThrottler:
    """Obtiene instancia singleton del LLMThrottler"""
    global _llm_throttler
    if _llm_throttler is None:
        _llm_throttler = LLMThrottler()
    return _llm_throttler
