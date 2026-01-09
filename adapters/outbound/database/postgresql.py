# Adaptador para PostgreSQL

import logging
from typing import Any, Dict, List, Optional, Tuple
import psycopg2

from adapters.outbound.database.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabaseAdapter):
    """Adaptador para bases de datos PostgreSQL"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

        self._psycopg2 = psycopg2

    def _get_connection(self):
        return self._psycopg2.connect(self.connection_string)

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
            logger.error(f"PostgreSQL error: {e}")
            return {"error": str(e)}

    def get_schemas(self) -> List[str]:
        result = self.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            AND schema_name NOT LIKE 'pg_%%'
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
            SELECT column_name, data_type, udt_name
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
