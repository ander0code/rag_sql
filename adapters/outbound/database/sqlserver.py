# Adaptador para SQL Server

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from adapters.outbound.database.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class SQLServerAdapter(DatabaseAdapter):
    """Adaptador para bases de datos Microsoft SQL Server"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._parse_connection()

    def _parse_connection(self):
        """Parsea connection string formato: mssql+pyodbc://user:pass@host:port/db?..."""
        match = re.match(
            r"mssql\+pyodbc://([^:]+):([^@]+)@([^:]+):(\d+)/(.+?)\?",
            self.connection_string,
        )
        if match:
            self.user, self.password, self.host, self.port, self.database = (
                match.groups()
            )
        else:
            raise ValueError(f"Invalid SQL Server connection string: {self.connection_string}")

    def _get_connection(self):
        import pyodbc  # type: ignore[import-not-found]

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password}"
        )
        return pyodbc.connect(conn_str)

    def execute(
        self, query: str, params: Optional[Tuple] = None
    ) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
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
        result = self.execute(
            """
            SELECT table_name FROM INFORMATION_SCHEMA.TABLES 
            WHERE table_schema = ? AND table_type = 'BASE TABLE'
            """,
            params=(schema,),
        )
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        result = self.execute(
            """
            SELECT column_name, data_type, data_type
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position
            """,
            params=(schema, table),
        )
        return [
            {"name": r[0], "type": r[1], "udt": r[2]} for r in result.get("data", [])
        ]

    def test_connection(self) -> bool:
        try:
            result = self.execute("SELECT 1")
            return "error" not in result
        except Exception:
            return False
