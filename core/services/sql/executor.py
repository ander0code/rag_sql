# Ejecutor de queries SQL contra PostgreSQL

import psycopg2
from contextlib import contextmanager
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Ejecuta queries SQL en modo solo-lectura
class QueryExecutor:
    def __init__(self, db_uri: str):
        self.db_uri = db_uri

    # Context manager para obtener cursor de DB
    @contextmanager
    def get_cursor(self):
        conn = psycopg2.connect(self.db_uri)
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            conn.close()

    def execute(
        self, query: str, params: Optional[Tuple] = None, timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Ejecuta query con parámetros opcionales.

        Args:
            query: SQL query (usar %s para parámetros)
            params: Tupla de parámetros (opcional)
            timeout: Timeout en segundos

        Returns:
            dict con columns y data, o error
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"SET statement_timeout = {timeout * 1000};")
                cursor.execute(query, params)
                return {
                    "columns": [d[0] for d in cursor.description],
                    "data": cursor.fetchall(),
                }
        except Exception as e:
            logger.error(f"Error SQL: {e}")
            return {"error": str(e)}

    def check_tables(self, schema: str, tables: list) -> dict:
        try:
            with self.get_cursor() as cursor:
                placeholders = ",".join(["%s"] * len(tables))
                cursor.execute(
                    f"""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name IN ({placeholders})
                """,
                    [schema] + tables,
                )
                existing = [r[0] for r in cursor.fetchall()]
                return {
                    "existing": existing,
                    "missing": [t for t in tables if t not in existing],
                    "found": len(existing),
                }
        except Exception as e:
            return {"existing": [], "missing": tables, "error": str(e)}

    def get_schemas(self) -> list:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT schema_name FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                """)
                return [r[0] for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error al obtener schemas: {e}")
            return []
