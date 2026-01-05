# Puerto de Base de Datos

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class DatabasePort(ABC):
    """Puerto para acceso a base de datos"""

    @abstractmethod
    def execute(self, query: str) -> Dict[str, Any]:
        """Ejecuta una query y retorna resultados"""
        pass

    @abstractmethod
    def get_schemas(self) -> List[str]:
        """Retorna lista de schemas disponibles"""
        pass

    @abstractmethod
    def get_tables(self, schema: str) -> List[Dict[str, Any]]:
        """Retorna tablas de un schema con sus columnas"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Verifica la conexión"""
        pass
