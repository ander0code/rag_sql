# Adaptadores de base de datos multi-tipo

import logging
import re
from typing import Any, Dict, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# Interfaz base para adaptadores de DB
class DatabaseAdapter(ABC):
    @abstractmethod
    def execute(self, query: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_schemas(self) -> List[str]:
        pass

    @abstractmethod
    def get_tables(self, schema: str) -> List[str]:
        pass

    @abstractmethod
    def get_columns(self, schema: str, table: str) -> List[Dict]:
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        pass


# Adaptador para PostgreSQL
class PostgreSQLAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        import psycopg2

        self._psycopg2 = psycopg2

    def _get_connection(self):
        return self._psycopg2.connect(self.connection_string)

    def execute(self, query: str) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        data = cursor.fetchall()
                        return {
                            "columns": columns,
                            "data": data,
                            "row_count": len(data),
                        }
                    return {"columns": [], "data": [], "row_count": 0}
        except Exception as e:
            logger.error(f"PostgreSQL error: {e}")
            return {"error": str(e)}

    def get_schemas(self) -> List[str]:
        result = self.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            AND schema_name NOT LIKE 'pg_%'
        """)
        return [r[0] for r in result.get("data", [])]

    def get_tables(self, schema: str) -> List[str]:
        result = self.execute(f"""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """)
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        result = self.execute(f"""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
        """)
        return [
            {"name": r[0], "type": r[1], "udt": r[2]} for r in result.get("data", [])
        ]

    def test_connection(self) -> bool:
        try:
            result = self.execute("SELECT 1")
            return "error" not in result
        except Exception:
            return False


# Adaptador para MySQL
class MySQLAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._parse_connection()

    def _parse_connection(self):
        match = re.match(
            r"mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+?)(?:\?|$)",
            self.connection_string,
        )
        if match:
            self.user, self.password, self.host, self.port, self.database = (
                match.groups()
            )
            self.port = int(self.port)
        else:
            raise ValueError("Invalid MySQL connection string")

    def _get_connection(self):
        import pymysql

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
        )

    def execute(self, query: str) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        data = cursor.fetchall()
                        return {
                            "columns": columns,
                            "data": data,
                            "row_count": len(data),
                        }
                    return {"columns": [], "data": [], "row_count": 0}
        except Exception as e:
            logger.error(f"MySQL error: {e}")
            return {"error": str(e)}

    def get_schemas(self) -> List[str]:
        result = self.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        """)
        return [r[0] for r in result.get("data", [])]

    def get_tables(self, schema: str) -> List[str]:
        result = self.execute(f"""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """)
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        result = self.execute(f"""
            SELECT column_name, data_type, column_type
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
        """)
        return [
            {"name": r[0], "type": r[1], "udt": r[2]} for r in result.get("data", [])
        ]

    def test_connection(self) -> bool:
        try:
            result = self.execute("SELECT 1")
            return "error" not in result
        except Exception:
            return False


# Adaptador para SQL Server
class SQLServerAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._parse_connection()

    def _parse_connection(self):
        match = re.match(
            r"mssql\+pyodbc://([^:]+):([^@]+)@([^:]+):(\d+)/(.+?)\?",
            self.connection_string,
        )
        if match:
            self.user, self.password, self.host, self.port, self.database = (
                match.groups()
            )
        else:
            raise ValueError("Invalid SQL Server connection string")

    def _get_connection(self):
        import pyodbc

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password}"
        )
        return pyodbc.connect(conn_str)

    def execute(self, query: str) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    data = cursor.fetchall()
                    return {
                        "columns": columns,
                        "data": [tuple(row) for row in data],
                        "row_count": len(data),
                    }
                return {"columns": [], "data": [], "row_count": 0}
        except Exception as e:
            logger.error(f"SQL Server error: {e}")
            return {"error": str(e)}

    def get_schemas(self) -> List[str]:
        result = self.execute("""
            SELECT name FROM sys.schemas 
            WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest', 'db_owner', 'db_accessadmin')
        """)
        return [r[0] for r in result.get("data", [])]

    def get_tables(self, schema: str) -> List[str]:
        result = self.execute(f"""
            SELECT table_name FROM INFORMATION_SCHEMA.TABLES 
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """)
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        result = self.execute(f"""
            SELECT column_name, data_type, data_type
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
        """)
        return [
            {"name": r[0], "type": r[1], "udt": r[2]} for r in result.get("data", [])
        ]

    def test_connection(self) -> bool:
        try:
            result = self.execute("SELECT 1")
            return "error" not in result
        except Exception:
            return False


# Factory para crear adaptador según tipo de DB
def get_database_adapter(db_type: str, connection_string: str) -> DatabaseAdapter:
    adapters = {
        "postgresql": PostgreSQLAdapter,
        "mysql": MySQLAdapter,
        "sqlserver": SQLServerAdapter,
    }

    adapter_class = adapters.get(db_type.lower())
    if not adapter_class:
        raise ValueError(f"Tipo de base de datos no soportado: {db_type}")

    return adapter_class(connection_string)
