# Puerto de Cache
# Define la interfaz que cualquier adaptador de cache debe implementar

from abc import ABC, abstractmethod
from typing import Optional, Any


class CachePort(ABC):
    """Puerto para acceso a cache"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del cache"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Guarda valor en cache"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Elimina valor del cache"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica conexión"""
        pass
