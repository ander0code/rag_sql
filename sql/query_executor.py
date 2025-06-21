import psycopg2
from contextlib import contextmanager
import logging

logger = logging.getLogger("uvicorn")

class SafePGExecutor:
    """
    Ejecutor seguro de consultas PostgreSQL con manejo de conexiones y timeouts.
    
    Características:
    - Conexiones con modo readonly
    - Timeout configurable
    - Manejo automático de recursos
    """
    def __init__(self, db_uri: str):
        self.db_uri = db_uri

    @contextmanager
    def get_cursor(self):
        """
        Context manager para manejo automático de conexiones.
        
        Garantiza:
        - Cierre correcto de cursor y conexión
        - Configuración de sesión como readonly
        """
        conn = psycopg2.connect(self.db_uri)
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            conn.close()

    def execute(self, query: str, timeout: int = 10) -> dict:
        """
        Ejecuta consulta SQL con protección contra queries largos.
        
        Retorna:
        - Dict con {columns, data} en éxito
        - Dict con {error} en fallo
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"SET statement_timeout = {timeout * 1000};")
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                return {"columns": columns, "data": data}
        except Exception as e:
            logger.error(f"Error en ejecución SQL: {e}")
            return {"error": str(e)}