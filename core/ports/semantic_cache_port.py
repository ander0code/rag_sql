# Puerto de Semantic Cache

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class SemanticCachePort(ABC):
    """Puerto para cache semántico basado en embeddings"""

    @abstractmethod
    def search(self, query: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """
        Busca query similar en el cache.

        Args:
            query: Query a buscar
            threshold: Umbral de similitud

        Returns:
            Dict con resultado si hay hit, None si no
        """
        pass

    @abstractmethod
    def save(self, query: str, sql: str, result: str, tables: List[str]) -> bool:
        """
        Guarda una query y su resultado en el cache.

        Args:
            query: Query original
            sql: SQL generado
            result: Resultado/respuesta
            tables: Tablas usadas

        Returns:
            True si se guardó correctamente
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el cache semántico está disponible"""
        pass
