# Interfaz base para adaptadores de base de datos

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseAdapter(ABC):
    """
    Interfaz abstracta para adaptadores de base de datos.
    Todos los adaptadores concretos deben implementar estos métodos.
    """

    @abstractmethod
    def execute(
        self, query: str, params: Optional[Tuple] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una query SQL.

        Args:
            query: SQL a ejecutar
            params: Parámetros para query parametrizada (opcional)

        Returns:
            Dict con columns, data, row_count o error
        """
        pass

    @abstractmethod
    def get_schemas(self) -> List[str]:
        """Retorna lista de schemas disponibles"""
        pass

    @abstractmethod
    def get_tables(self, schema: str) -> List[str]:
        """Retorna lista de tablas en un schema"""
        pass

    @abstractmethod
    def get_columns(self, schema: str, table: str) -> List[Dict]:
        """Retorna lista de columnas de una tabla"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Verifica si la conexión funciona"""
        pass
