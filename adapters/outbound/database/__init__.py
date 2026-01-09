# Adaptadores de base de datos - Factory y re-exports

from adapters.outbound.database.base import DatabaseAdapter
from adapters.outbound.database.postgresql import PostgreSQLAdapter
from adapters.outbound.database.mysql import MySQLAdapter
from adapters.outbound.database.sqlserver import SQLServerAdapter
from adapters.outbound.database.sqlite import SQLiteAdapter


def get_database_adapter(db_type: str, connection_string: str) -> DatabaseAdapter:
    """
    Factory para crear el adaptador correcto según tipo de DB.

    Args:
        db_type: Tipo de base de datos (postgresql, mysql, sqlserver, sqlite)
        connection_string: String de conexión

    Returns:
        DatabaseAdapter concreto para el tipo especificado

    Raises:
        ValueError: Si el tipo de DB no está soportado
    """
    adapters = {
        "postgresql": PostgreSQLAdapter,
        "postgres": PostgreSQLAdapter,
        "mysql": MySQLAdapter,
        "mariadb": MySQLAdapter,
        "sqlserver": SQLServerAdapter,
        "mssql": SQLServerAdapter,
        "sqlite": SQLiteAdapter,
    }

    adapter_class = adapters.get(db_type.lower())
    if not adapter_class:
        supported = ", ".join(sorted(set(adapters.keys())))
        raise ValueError(
            f"Tipo de base de datos no soportado: '{db_type}'. "
            f"Soportados: {supported}"
        )

    return adapter_class(connection_string)


__all__ = [
    "DatabaseAdapter",
    "PostgreSQLAdapter",
    "MySQLAdapter",
    "SQLServerAdapter",
    "SQLiteAdapter",
    "get_database_adapter",
]
