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

    def check_schema_tables(self, schema_name: str, table_names: list) -> dict:
        """
        Verifica si las tablas existen en el schema especificado.
        
        Args:
            schema_name: Nombre del schema a verificar
            table_names: Lista de nombres de tablas a verificar
            
        Returns:
            Dict con información sobre tablas existentes y faltantes
        """
        try:
            with self.get_cursor() as cursor:
                # Consulta para verificar existencia de tablas en el schema
                placeholders = ','.join(['%s'] * len(table_names))
                query = f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name IN ({placeholders})
                """
                cursor.execute(query, [schema_name] + table_names)
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [t for t in table_names if t not in existing_tables]
                
                return {
                    "schema_exists": len(existing_tables) > 0,
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "total_requested": len(table_names),
                    "total_found": len(existing_tables)
                }
        except Exception as e:
            logger.error(f"Error verificando tablas en schema {schema_name}: {e}")
            return {
                "schema_exists": False,
                "existing_tables": [],
                "missing_tables": table_names,
                "error": str(e)
            }

    def get_available_schemas(self) -> list:
        """
        Obtiene lista de schemas disponibles en la base de datos.
        
        Returns:
            Lista de nombres de schemas
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY schema_name
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo schemas disponibles: {e}")
            return []