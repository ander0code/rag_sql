# Adaptador para MySQL

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from adapters.outbound.database.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class MySQLAdapter(DatabaseAdapter):
    """Adaptador para bases de datos MySQL/MariaDB"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._parse_connection()

    def _parse_connection(self):
        """Parsea connection string formato: mysql+pymysql://user:pass@host:port/db"""
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
            raise ValueError(f"Invalid MySQL connection string: {self.connection_string}")

    def _get_connection(self):
        import pymysql  # type: ignore[import-not-found]

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
        )

    def execute(
        self, query: str, params: Optional[Tuple] = None
    ) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
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
        result = self.execute(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """,
            params=(schema,),
        )
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        result = self.execute(
            """
            SELECT column_name, data_type, column_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
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
