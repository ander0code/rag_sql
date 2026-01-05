# Core Ports - Interfaces for external dependencies

from core.ports.database_port import DatabasePort
from core.ports.llm_port import LLMPort
from core.ports.cache_port import CachePort

__all__ = ["DatabasePort", "LLMPort", "CachePort"]
