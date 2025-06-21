import logging
# from functools import lru_cache
from sql.semantic_retriever import SchemaRetriever
from sql.sql_generator import SQLGenerator
from sql.query_executor import SafePGExecutor
from config.settings import settings

logger = logging.getLogger(__name__)

retriever = SchemaRetriever()
generator = SQLGenerator()
executor = SafePGExecutor(db_uri=settings.db.db_uri)


# cachear schemas 
# @lru_cache(maxsize=100)
# def get_relevant_schemas_cached(query: str) -> list:
#     """Cachea resultados de recuperación de esquemas para consultas repetidas."""
#     return retriever.get_relevant_tables(query)

def is_valid_sql(sql: str) -> bool:
    """Valida que el SQL no contenga operaciones peligrosas."""
    dangerous_keywords = ["DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE", "ALTER"]
    
    normalized_sql = sql.upper()
    
    for kw in dangerous_keywords:
        if f" {kw} " in f" {normalized_sql} ":  
            logger.warning(f"SQL contiene operación peligrosa: {kw}")
            return False
    
    if "SELECT" not in normalized_sql:
        logger.warning("SQL no contiene operación SELECT")
        return False
        
    logger.debug(f"SQL validado correctamente: {sql[:100]}...")
    return True

def full_pipeline(query: str) -> str:
    """
    Pipeline principal de ejecución de consultas.
    
    Flujo de trabajo:
    1. Recuperación de esquemas relevantes
    2. Expansión de esquemas con relaciones
    3. Generación de SQL
    4. Ejecución y validación
    5. Generación de respuesta natural
    """
    logger.info(f"Iniciando pipeline para consulta: '{query}'")
    
    # Fase 1: Recuperación de esquemas
    relevant_schemas = retriever.get_relevant_tables(query)
    logger.info("--- Tablas iniciales ---")
    for schema in relevant_schemas:
        table_name = schema["metadata"].get("table_name", "Desconocida")
        logger.info(f"Tabla: {table_name} (Score: {schema['score']:.2f})")
    
    # Fase 2: Expansión de contexto
    expanded_schemas = retriever.expand_schemas(relevant_schemas)
    logger.info("--- Esquemas expandidos ---")
    for s in expanded_schemas:
        logger.info(f"Tabla: {s['metadata']['table_name']}")
    
    # Fase 3: Generación SQL
    sql_query = generator.generate_sql_and_response(query, expanded_schemas)
    logger.info("--- SQL generado ---")
    logger.info(sql_query)
    
    if not is_valid_sql(sql_query):
        logger.warning("SQL no válido detectado")
        return "Error: Consulta no válida."
    
    # Fase 4: Ejecución
    result = executor.execute(sql_query)
    if "error" in result:
        logger.error(f"Error en ejecución: {result['error']}")
        return f"Error en ejecución: {result['error']}"
    
    logger.debug("Resultado de la consulta SQL:")
    logger.debug(result)
    
    # Fase 5: Generación de respuesta
    if not result.get("data"):
        logger.info("No se encontraron resultados")
        final_response = generator.generate_response_from_result(
            query, 
            expanded_schemas, 
            {"data": [], "columns": [], "message": "No se encontraron resultados"}
        )
        logger.info("--- Respuesta final generada (sin resultados) ---")
    else:

        logger.info(f"Se encontraron {len(result.get('data', []))} resultados")
        final_response = generator.generate_response_from_result(
            query,
            expanded_schemas,
            result
        )
        logger.info("--- Respuesta final generada (con resultados) ---")
    
    return final_response