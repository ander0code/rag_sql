import logging
from sql.semantic_retriever import SchemaRetriever
from sql.sql_generator import SQLGenerator
from sql.query_executor import SafePGExecutor
from config.settings import settings

logger = logging.getLogger(__name__)

retriever = SchemaRetriever()
generator = SQLGenerator()
executor = SafePGExecutor(db_uri=settings.db.db_uri)

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
    Pipeline principal de ejecución de consultas MULTI-TENANT INTELIGENTE.
    
    Flujo de trabajo:
    1. Validación de schema y tablas
    2. Recuperación de esquemas relevantes
    3. Clasificación automática por schema (public vs tenant)
    4. Verificación inteligente en schemas correctos
    5. Generación de SQL con prefijos automáticos
    6. Ejecución y validación
    7. Generación de respuesta natural
    
    Args:
        query: Consulta en lenguaje natural
        schema: Schema de la base de datos TENANT a consultar (para tablas específicas del tenant)
    """
    if not schema or schema.strip() == "":
        logger.error("Schema no proporcionado - es obligatorio")
        return "Error: Debe especificar un schema válido."
    
    logger.info(f"Iniciando pipeline multi-tenant para consulta: '{query}' en schema tenant: '{schema}'")
    
    # Fase 0: Validación de schemas disponibles
    logger.info("--- Validando schemas disponibles ---")
    
    available_schemas = executor.get_available_schemas()
    logger.info(f"Schemas disponibles: {available_schemas}")
    
    if schema not in available_schemas:
        logger.error(f"Schema tenant '{schema}' no existe en la base de datos")
        return f"Error: El schema '{schema}' no existe. Schemas disponibles: {', '.join(available_schemas)}"
    
    # Fase 1: Recuperación de esquemas (100% LLM-DRIVEN)
    relevant_schemas = retriever.get_relevant_tables(query)
    logger.info("--- Tablas seleccionadas por LLM ---")
    for schema_item in relevant_schemas:
        table_name = schema_item["metadata"].get("table_name", "Desconocida")
        schema_type = schema_item["metadata"].get("schema", "tenant")
        logger.info(f"Tabla: {table_name} (schema: {schema_type})")
    
    # NUEVO: Clasificación automática de tablas por schema
    logger.info("--- Clasificación automática multi-tenant ---")
    public_tables = []
    tenant_tables = []
    
    for schema_item in relevant_schemas:
        table_name = schema_item["metadata"]["table_name"]
        schema_type = schema_item["metadata"].get("schema", "tenant")
        
        if schema_type == "public":
            public_tables.append(schema_item)
            logger.info(f"✅ {table_name} → schema PUBLIC (centralizada)")
        else:
            tenant_tables.append(schema_item)
            logger.info(f"✅ {table_name} → schema TENANT '{schema}' (específica)")
    
    logger.info(f"📊 Distribución final: PUBLIC({len(public_tables)}), TENANT({len(tenant_tables)})")
    
    # NUEVO: Verificación inteligente por schema type
    logger.info("--- Verificación inteligente multi-schema ---")
    valid_schemas = []
    validation_errors = []
    
    # Verificar tablas PUBLIC
    if public_tables:
        public_table_names = [s["metadata"]["table_name"] for s in public_tables]
        public_check = executor.check_schema_tables("public", public_table_names)
        
        logger.info(f"Verificación PUBLIC: {public_check['total_found']}/{public_check['total_requested']} encontradas")
        
        if public_check["missing_tables"]:
            logger.warning(f"Tablas PUBLIC faltantes: {public_check['missing_tables']}")
            validation_errors.extend([f"Tabla PUBLIC '{t}' no encontrada" for t in public_check["missing_tables"]])
        
        # Añadir tablas públicas válidas
        for schema_item in public_tables:
            if schema_item["metadata"]["table_name"] in public_check["existing_tables"]:
                valid_schemas.append(schema_item)
    
    # Verificar tablas TENANT
    if tenant_tables:
        tenant_table_names = [s["metadata"]["table_name"] for s in tenant_tables]
        tenant_check = executor.check_schema_tables(schema, tenant_table_names)
        
        logger.info(f"Verificación TENANT '{schema}': {tenant_check['total_found']}/{tenant_check['total_requested']} encontradas")
        
        if tenant_check["missing_tables"]:
            logger.warning(f"Tablas TENANT faltantes en '{schema}': {tenant_check['missing_tables']}")
            validation_errors.extend([f"Tabla TENANT '{t}' no encontrada en schema '{schema}'" for t in tenant_check["missing_tables"]])
        
        # Añadir tablas tenant válidas
        for schema_item in tenant_tables:
            if schema_item["metadata"]["table_name"] in tenant_check["existing_tables"]:
                valid_schemas.append(schema_item)
    
    # Verificar que tengamos al menos una tabla válida
    if not valid_schemas:
        logger.error("No hay tablas válidas después de la verificación multi-schema")
        error_msg = "Error: No se encontraron tablas válidas.\n"
        if validation_errors:
            error_msg += "Problemas detectados:\n" + "\n".join(validation_errors)
        return error_msg
    
    if validation_errors:
        logger.info(f"Continuando con {len(valid_schemas)} tablas válidas (algunas faltantes)")
    
    # Fase 2: Expansión de contexto (solo si es necesario y válido)
    if len(valid_schemas) <= 2:
        logger.info("--- Saltando expansión para consulta simple ---")
        final_schemas = valid_schemas
    else:
        expanded_schemas = retriever.expand_schemas(valid_schemas)
        logger.info("--- Esquemas expandidos ---")
        
        # NUEVO: Validar esquemas expandidos también
        final_schemas = []
        for expanded_schema in expanded_schemas:
            table_name = expanded_schema["metadata"]["table_name"]
            expanded_schema_type = expanded_schema["metadata"].get("schema", "tenant")
            
            # Verificar en el schema correcto
            target_schema_check = "public" if expanded_schema_type == "public" else schema
            table_check = executor.check_schema_tables(target_schema_check, [table_name])
            
            if table_check["total_found"] > 0:
                final_schemas.append(expanded_schema)
                logger.info(f"Tabla expandida válida: {table_name} en {target_schema_check}")
            else:
                logger.warning(f"Tabla expandida inválida: {table_name} no existe en {target_schema_check}")
        
        if not final_schemas:
            logger.warning("Expansión resultó en tablas inválidas, usando esquemas originales")
            final_schemas = valid_schemas
    
    logger.info(f"Tablas finales para SQL: {[s['metadata']['table_name'] for s in final_schemas]}")
    
    # Fase 3: Generación SQL con detección automática de schemas
    logger.info(f"Generando SQL multi-tenant con schema objetivo: {schema}")
    sql_query = generator.generate_sql_and_response(query, final_schemas, target_schema=schema)
    logger.info("--- SQL generado COMPLETO ---")
    logger.info(f"SQL COMPLETO: {sql_query}")  # NUEVO: Log completo sin truncar
    
    if not is_valid_sql(sql_query):
        logger.warning("SQL no válido detectado")
        return "Error: Consulta no válida."
    
    # Fase 4: Ejecución
    result = executor.execute(sql_query)
    if "error" in result:
        logger.error(f"Error en ejecución COMPLETO: {result['error']}")
        logger.error(f"SQL que causó el error: {sql_query}")  # NUEVO: Mostrar SQL completo en errores
        return f"Error en ejecución: {result['error']}\n\nSQL ejecutado: {sql_query}"
    
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
    
    # Mostrar resumen final con enfoque multi-tenant
    print("\n🤖 === RESUMEN FINAL - MULTI-TENANT INTELIGENTE ===")
    print(f"❓ Consulta: {query}")
    print(f"🗂️ Schema TENANT objetivo: {schema}")
    print(f"📊 Tablas PUBLIC usadas: {len(public_tables)}")
    print(f"📊 Tablas TENANT usadas: {len(tenant_tables)}")
    print(f"📈 Resultados encontrados: {len(result.get('data', []))}")
    print("🧠 Detección automática: Cada tabla usa su schema correcto")
    print("🎯 0% hardcoding: Clasificación basada en metadata")
    print("=" * 50)
    
    return final_response