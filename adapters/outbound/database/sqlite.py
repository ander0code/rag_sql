# Adaptador para SQLite

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from adapters.outbound.database.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class SQLiteAdapter(DatabaseAdapter):
    """Adaptador para bases de datos SQLite"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._parse_connection()

    def _parse_connection(self):
        """Parsea connection string formato: sqlite:///path/to/db.sqlite"""
        match = re.match(r"sqlite:///(.+)", self.connection_string)
        if match:
            self.db_path = match.group(1)
        else:
            # Asumir que es directamente el path
            self.db_path = self.connection_string

    def _get_connection(self):
        import sqlite3

        return sqlite3.connect(self.db_path)

    def execute(
        self, query: str, params: Optional[Tuple] = None
    ) -> Dict[str, Any]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                conn.close()
                return {
                    "columns": columns,
                    "data": data,
                    "row_count": len(data),
                }
            conn.close()
            return {"columns": [], "data": [], "row_count": 0}
        except Exception as e:
            logger.error(f"SQLite error: {e}")
            return {"error": str(e)}

    def get_schemas(self) -> List[str]:
        """SQLite no tiene schemas, retorna 'main' por defecto"""
        return ["main"]

    def get_tables(self, schema: str = "main") -> List[str]:
        result = self.execute("""
            SELECT name FROM sqlite_master 
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """)
        return [r[0] for r in result.get("data", [])]

    def get_columns(self, schema: str, table: str) -> List[Dict]:
        # SQLite usa PRAGMA para info de columnas
        result = self.execute(f"PRAGMA table_info({table})")
        # PRAGMA retorna: cid, name, type, notnull, dflt_value, pk
        return [
            {"name": r[1], "type": r[2], "udt": r[2]} for r in result.get("data", [])
        ]

    def test_connection(self) -> bool:
        try:
            result = self.execute("SELECT 1")
            return "error" not in result
        except Exception:
            return False
