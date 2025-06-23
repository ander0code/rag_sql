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

def full_pipeline(query: str, schema: str) -> str:
    """
    Pipeline principal de ejecución de consultas.
    
    Flujo de trabajo:
    1. Validación de schema y tablas
    2. Recuperación de esquemas relevantes
    3. Expansión de esquemas con relaciones
    4. Generación de SQL con schema específico
    5. Ejecución y validación
    6. Generación de respuesta natural
    
    Args:
        query: Consulta en lenguaje natural
        schema: Schema de la base de datos a consultar (OBLIGATORIO)
    """
    if not schema or schema.strip() == "":
        logger.error("Schema no proporcionado - es obligatorio")
        return "Error: Debe especificar un schema válido."
    
    logger.info(f"Iniciando pipeline para consulta: '{query}' en schema: '{schema}'")
    
    # Fase 0: Validación de schema y tablas
    logger.info("--- Validando schema y tablas ---")
    
    # Obtener schemas disponibles
    available_schemas = executor.get_available_schemas()
    logger.info(f"Schemas disponibles: {available_schemas}")
    
    if schema not in available_schemas:
        logger.error(f"Schema '{schema}' no existe en la base de datos")
        return f"Error: El schema '{schema}' no existe. Schemas disponibles: {', '.join(available_schemas)}"
    
    # Fase 1: Recuperación de esquemas (100% LLM-DRIVEN)
    relevant_schemas = retriever.get_relevant_tables(query)
    logger.info("--- Tablas seleccionadas por LLM ---")
    for schema_item in relevant_schemas:
        table_name = schema_item["metadata"].get("table_name", "Desconocida")
        logger.info(f"Tabla: {table_name}")
    
    # Mostrar que ahora es inteligente, no hardcodeado
    total_available = len(retriever.schemas)
    selected_count = len(relevant_schemas)
    logger.info(f"🤖 Selección LLM: {selected_count}/{total_available} tablas (decisión inteligente del modelo)")
    
    # Verificar si las tablas existen en el schema objetivo
    table_names = [s["metadata"]["table_name"] for s in relevant_schemas]
    table_check = executor.check_schema_tables(schema, table_names)
    
    logger.info(f"Verificación de tablas: {table_check['total_found']}/{table_check['total_requested']} encontradas")
    
    if table_check["total_found"] == 0:
        logger.error(f"Ninguna tabla requerida existe en el schema '{schema}'")
        return f"Error: Las tablas necesarias ({', '.join(table_names)}) no existen en el schema '{schema}'. Tablas disponibles en otros schemas."
    
    if table_check["missing_tables"]:
        logger.warning(f"Tablas faltantes en schema '{schema}': {table_check['missing_tables']}")
        # Filtrar solo las tablas que existen
        relevant_schemas = [s for s in relevant_schemas if s["metadata"]["table_name"] in table_check["existing_tables"]]
        logger.info(f"Continuando con {len(relevant_schemas)} tablas disponibles")
    
    # Fase 2: Expansión de contexto (solo si es necesario)
    if len(relevant_schemas) <= 2:
        # Para consultas simples, evitar expansión innecesaria
        logger.info("--- Saltando expansión para consulta simple ---")
        expanded_schemas = relevant_schemas
    else:
        expanded_schemas = retriever.expand_schemas(relevant_schemas)
        logger.info("--- Esquemas expandidos ---")
        for s in expanded_schemas:
            logger.info(f"Tabla: {s['metadata']['table_name']}")
    
    # Verificar tablas expandidas también
    expanded_table_names = [s["metadata"]["table_name"] for s in expanded_schemas]
    expanded_check = executor.check_schema_tables(schema, expanded_table_names)
    
    # Filtrar esquemas expandidos para incluir solo tablas existentes
    final_schemas = [s for s in expanded_schemas if s["metadata"]["table_name"] in expanded_check["existing_tables"]]
    
    if not final_schemas:
        logger.error("No hay tablas válidas después de la expansión y validación")
        return f"Error: No se encontraron tablas válidas en el schema '{schema}' para procesar la consulta."
    
    logger.info(f"Tablas finales para SQL: {[s['metadata']['table_name'] for s in final_schemas]}")
    
    # Fase 3: Generación SQL con schema específico
    logger.info(f"Generando SQL para schema: {schema}")
    sql_query = generator.generate_sql_and_response(query, final_schemas, target_schema=schema)
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
            final_schemas, 
            {"data": [], "columns": [], "message": "No se encontraron resultados"}
        )
        logger.info("--- Respuesta final generada (sin resultados) ---")
    else:
        logger.info(f"Se encontraron {len(result.get('data', []))} resultados")
        final_response = generator.generate_response_from_result(
            query,
            final_schemas,
            result
        )
        logger.info("--- Respuesta final generada (con resultados) ---")
    
    # Mostrar resumen final con nuevo enfoque
    print("\n🤖 === RESUMEN FINAL - 100% LLM DRIVEN ===")
    print(f"❓ Consulta: {query}")
    print(f"🗂️ Schema: {schema}")
    print(f"📋 Tablas disponibles: {total_available}")
    print(f"🤖 Tablas seleccionadas por LLM: {len(final_schemas)}")
    print(f"📈 Resultados encontrados: {len(result.get('data', []))}")
    print("🧠 Nota: Selección de tablas 100% inteligente - el LLM decide qué es necesario")
    print("=" * 50)
    
    return final_response