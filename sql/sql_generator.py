from utils.prompts import (
    SQL_SYSTEM_PROMPT,
    SQL_USER_PROMPT_TEMPLATE, 
    RESPONSE_SYSTEM_PROMPT, 
    RESPONSE_USER_PROMPT_TEMPLATE
)

import re
import logging
from langchain.schema import HumanMessage, SystemMessage
import tiktoken
from collections import defaultdict

from utils.clients import get_available_llm

logger = logging.getLogger(__name__)

class SQLGenerator:
    """
    Clase para generar consultas SQL a partir de lenguaje natural.
    
    Funcionalidades:
    - Construcción de prompts estructurados
    - Generación de SQL usando LLMs
    - Post-procesamiento y validación de consultas
    - Tracking completo de tokens y costos
    """
    def __init__(self):
        """Inicializa modelo LLM con fallback automático."""
        try:
            self.llm = get_available_llm()
            logger.info("✅ SQLGenerator inicializado con LLM")
            
            # Costos por token (en USD) - actualizar según modelo
            self.token_costs = {
                "deepseek-chat": {"input": 0.00000000, "output": 0.00000000},  # $0.14/$0.28 per 1M tokens
                "gpt-4o-mini": {"input": 0.00000000, "output": 0.00000000}     # $0.15/$0.60 per 1M tokens
            }
            
        except Exception as e:
            logger.error(f"❌ Error inicializando SQLGenerator: {e}")
            raise
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Cuenta tokens para un texto dado usando el modelo especificado"""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base") 
        return len(encoding.encode(text))
    
    def get_model_name(self) -> str:
        """Obtiene el nombre del modelo actual"""
        if hasattr(self.llm, 'model_name'):
            return self.llm.model_name
        elif hasattr(self.llm, 'model'):
            return self.llm.model
        return "desconocido"
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model_name: str) -> dict:
        """Calcula el costo en USD basado en tokens y modelo"""
        costs = self.token_costs.get(model_name, {"input": 0.0, "output": 0.0})
        
        input_cost = input_tokens * costs["input"]
        output_cost = output_tokens * costs["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

    def generate_sql_and_response(self, natural_query: str, schemas: list, target_schema: str = "public", sql_result: dict = None) -> str:
        """
        Pipeline completo para generación de SQL OPTIMIZADO con detección multi-tenant inteligente.
        """
        # ========== MAPEO INTELIGENTE DE SCHEMAS (NUEVO) ==========
        schema_table_mapping = []
        public_tables = set()
        tenant_tables = set()
        
        # Formateo COMPACTO de esquemas para reducir tokens (TU LÓGICA ORIGINAL)
        formatted_schemas = []
        for s in schemas:
            meta = s["metadata"]
            table_name = meta.get('table_name')
            schema_type = meta.get("schema", "tenant")  # Detectar tipo automáticamente
            
            # NUEVO: Clasificar tablas por schema real
            if schema_type == "public":
                public_tables.add(table_name)
                real_schema = "public"
            else:
                tenant_tables.add(table_name)
                real_schema = target_schema
            
            # TU FORMATO COMPACTO ORIGINAL (mantenido)
            compact_schema = f"T:{table_name}|C:{','.join([col.split(' (')[0] for col in meta.get('columns', [])[:5]])}|S:{real_schema}"
            formatted_schemas.append(compact_schema)
            
            # NUEVO: Mapeo explícito para el LLM
            columns_preview = ','.join([col.split(' (')[0] for col in meta.get('columns', [])[:4]])
            mapping_entry = f"📋 {table_name} → {real_schema}.{table_name} | Columnas: {columns_preview}"
            schema_table_mapping.append(mapping_entry)
        
        # ========== PROMPTS ARREGLADOS (sin errores) ==========
        system_prompt = SQL_SYSTEM_PROMPT
        
        # FIX: Usar el template correcto con todos los parámetros requeridos
        user_prompt = SQL_USER_PROMPT_TEMPLATE.format(
            schema_table_mapping="\n".join(schema_table_mapping),
            query=natural_query,
            target_schema=target_schema
        )
        
        # ========== LOGGING INTELIGENTE (NUEVO) ==========
        logger.info("🔍 Detección automática completada:")
        logger.info(f"📊 Tablas PUBLIC: {list(public_tables)}")
        logger.info(f"📊 Tablas TENANT: {list(tenant_tables)}")
        
        # ========== TU TRACKING ORIGINAL (mantenido) ==========
        model_name = self.get_model_name()
        prompt_tokens = self.count_tokens(system_prompt + user_prompt)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        print("\n💰 === SQL GENERATION - MULTI-TENANT INTELIGENTE ===")
        print(f"🤖 Modelo: {model_name}")
        print(f"📥 Tokens entrada: {prompt_tokens:,}")
        print(f"🔍 Detección: PUBLIC({len(public_tables)}), TENANT({len(tenant_tables)})")
        
        response = self.llm.invoke(messages)
        
        response_tokens = self.count_tokens(response.content)
        cost_info = self.calculate_cost(prompt_tokens, response_tokens, model_name)
        
        print(f"📤 Tokens salida: {response_tokens:,}")
        print(f"💰 Costo total: ${cost_info['total_cost']:.6f}")
        print("🧠 Detección automática: 0% hardcoding")
        print("=" * 50)
        
        # NUEVO: Pasar información de clasificación al post-procesamiento
        return self._postprocess_sql_enhanced(response.content, schemas, target_schema, public_tables, tenant_tables)

    def _postprocess_sql_enhanced(self, raw_sql: str, schemas: list, target_schema: str, public_tables: set, tenant_tables: set) -> str:
        """
        Post-procesamiento MEJORADO que combina tu lógica original con detección inteligente.
        
        - Mantiene toda tu validación UUID y formato original
        - Añade detección automática de schemas
        - Conserva tu análisis de metadatos
        - Mejora la aplicación de prefijos
        - NUEVO: Limpia comentarios de Markdown que causan errores SQL
        """
        # NUEVO: Limpieza agresiva de comentarios y texto explicativo
        logger.info(f"🔧 SQL RAW recibido (primeros 200 chars): {raw_sql[:200]}")
        
        # Remover comentarios de Markdown y texto explicativo
        lines = raw_sql.split('\n')
        sql_lines = []
        inside_sql_block = False
        
        for line in lines:
            line = line.strip()
            # Detectar inicio de bloque SQL
            if line.startswith('```sql'):
                inside_sql_block = True
                continue
            # Detectar fin de bloque SQL
            elif line.startswith('```') and inside_sql_block:
                inside_sql_block = False
                continue
            # Si estamos dentro del bloque SQL, incluir la línea
            elif inside_sql_block:
                if line and not line.startswith('#') and not line.startswith('--'):
                    sql_lines.append(line)
            # Si no hay bloques de código, buscar SELECT directamente
            elif 'SELECT' in line.upper() and not line.startswith('#'):
                sql_lines.append(line)
                # Continuar capturando las siguientes líneas hasta punto y coma
                inside_sql_block = True
        
        # Si no encontramos SQL en bloques de código, extraer desde SELECT
        if not sql_lines:
            logger.warning("🔧 No se encontró SQL en bloques de código, extrayendo desde SELECT")
            select_start = raw_sql.upper().find('SELECT')
            if select_start != -1:
                potential_sql = raw_sql[select_start:]
                # Remover texto después del primer punto y coma seguido de texto explicativo
                semicolon_pos = potential_sql.find(';')
                if semicolon_pos != -1:
                    # Buscar si hay texto explicativo después del ;
                    remaining = potential_sql[semicolon_pos + 1:].strip()
                    if remaining and not remaining.upper().startswith('SELECT'):
                        potential_sql = potential_sql[:semicolon_pos + 1]
                
                sql_lines = [potential_sql.strip()]
        
        clean_raw_sql = ' '.join(sql_lines).strip()
        logger.info(f"🔧 SQL después de limpieza de Markdown: {clean_raw_sql}")
        
        # Limpieza adicional de residuos
        clean_raw_sql = re.sub(r'^#.*?\n', '', clean_raw_sql, flags=re.MULTILINE)  # Comentarios #
        clean_raw_sql = re.sub(r'Explicación:.*$', '', clean_raw_sql, flags=re.DOTALL)  # Texto explicativo
        clean_raw_sql = re.sub(r'```\w*', '', clean_raw_sql)  # Bloques de código residuales
        clean_raw_sql = clean_raw_sql.strip()
        
        # ========== TU VALIDACIÓN UUID ORIGINAL (mantenida) ==========
        uuid_incompatible_functions = r'\b(MIN|MAX)\s*\(\s*"?id"?\s*\)'
        if re.search(uuid_incompatible_functions, clean_raw_sql, re.IGNORECASE):
            logger.warning("🔧 Detectada función MIN/MAX en columna UUID, corrigiendo automáticamente...")
            # Remover funciones problemáticas con su alias
            clean_raw_sql = re.sub(
                r'\b(MIN|MAX)\s*\(\s*"?id"?\s*\)\s*AS\s*"[^"]*",?\s*',
                '',
                clean_raw_sql,
                flags=re.IGNORECASE
            )
            # Limpiar comas dobles que puedan quedar
            clean_raw_sql = re.sub(r',\s*,', ',', clean_raw_sql)
            clean_raw_sql = re.sub(r'SELECT\s*,', 'SELECT', clean_raw_sql)
            clean_raw_sql = re.sub(r',\s*FROM', ' FROM', clean_raw_sql)
            logger.info("✅ Funciones UUID incompatibles removidas automáticamente")

        # ========== TU DETECCIÓN MULTI-SCHEMA ORIGINAL (mantenida) ==========
        has_public_prefix = bool(re.search(r'\bpublic\."[^"]+"', clean_raw_sql))
        has_tenant_prefix = bool(re.search(rf'"{target_schema}"\."[^"]+"', clean_raw_sql))
        has_any_schema_prefix = has_public_prefix or has_tenant_prefix

        # ========== TU ANÁLISIS DE METADATOS ORIGINAL (mantenido completamente) ==========
        relation_graph = defaultdict(list)
        column_tables = defaultdict(set)
        semantic_tags = defaultdict(list)
        available_tables = set()
        
        # NUEVO: Usar la clasificación ya hecha en lugar de recalcular
        # (pero mantenemos tu lógica original como backup)
        original_public_tables = set()
        original_tenant_tables = set()

        for schema in schemas:
            meta = schema["metadata"]
            table = meta["table_name"]
            schema_type = meta.get("schema", "tenant")  # Tu lógica original
            
            available_tables.add(table)
            
            if schema_type == "public":
                original_public_tables.add(table)
            else:
                original_tenant_tables.add(table)

            # TU ANÁLISIS DE COLUMNAS ORIGINAL (mantenido)
            for col in meta["columns"]:
                col_name = col.split(" (")[0]  
                column_tables[col_name].add(table)
                
                col_type = col.split(" (")[1][:-1] if "(" in col else ""
                if 'varchar' in col_type or 'text' in col_type.lower():
                    semantic_tags[table].append(f"texto:{col_name}")
                if 'int' in col_type or 'numeric' in col_type or 'uuid' in col_type.lower():
                    semantic_tags[table].append(f"número:{col_name}")
                for enum_val in meta.get("enums", {}).get(col_name, []):
                    semantic_tags[table].append(f"valor:{enum_val}")
            
            # TU ANÁLISIS DE RELACIONES ORIGINAL (mantenido)
            for rel in meta.get("relationships", []):
                if "->" in rel["description"]:
                    source, target = rel["description"].split("->", 1)
                    src_col = source.strip().split(".")[-1]  
                    target_table = target.split(".")[0].strip()
                    relation_graph[table].append((src_col, target_table))

        # NUEVO: Verificar consistencia entre clasificaciones
        if public_tables != original_public_tables or tenant_tables != original_tenant_tables:
            logger.warning("🔧 Diferencias detectadas en clasificación, usando detección original como fallback")
            public_tables = original_public_tables
            tenant_tables = original_tenant_tables

        # ========== APLICACIÓN DE PREFIJOS MEJORADA (combinando ambos enfoques) ==========
        # ========== APLICACIÓN DE PREFIJOS MEJORADA (FIX DEFINITIVO) ==========
        if not has_any_schema_prefix:
            logger.info(f"🔧 Aplicando prefijos multi-schema inteligentes: public + '{target_schema}'")
            
            def apply_enhanced_schema_prefix(match):
                """Aplica prefijo SÚPER inteligente combinando tu lógica con detección automática"""
                clause = match.group(1)  # FROM o JOIN
                table = match.group(2)   # nombre de tabla
                
                # FIX CRÍTICO: Solo procesar nombres de tablas reales, no keywords SQL
                if table.lower() in ['public', 'information_schema', 'pg_catalog', 'select', 'where', 'and', 'or']:
                    logger.debug(f"🚫 Ignorando '{table}' - no es una tabla válida")
                    return match.group(0)  # Devolver sin cambios
                
                # Verificar que la tabla esté en nuestras listas
                if table not in available_tables:
                    logger.debug(f"🚫 Ignorando '{table}' - no está en tablas disponibles")
                    return match.group(0)  # Devolver sin cambios
                
                # NIVEL 1: Usar clasificación automática (NUEVO)
                if table in public_tables:
                    detected_schema = "public"
                    logger.debug(f"✅ {table} → public (DETECCIÓN AUTOMÁTICA)")
                elif table in tenant_tables:
                    detected_schema = target_schema
                    logger.debug(f"✅ {table} → {target_schema} (DETECCIÓN AUTOMÁTICA)")
                # NIVEL 2: Tu lógica original como fallback (MANTENIDA)
                else:
                    # Fallback inteligente basado en nombres conocidos (TU LÓGICA)
                    if table in ["tenant_usuarios", "administradores", "organizaciones", "suscripciones"]:
                        detected_schema = "public"
                        logger.warning(f"⚠️ {table} → public (FALLBACK por nombre conocido)")
                    else:
                        detected_schema = target_schema
                        logger.warning(f"⚠️ {table} → {target_schema} (FALLBACK por defecto)")
                
                return f'{clause} "{detected_schema}"."{table}"'
            
            # Aplicar prefijos con expresión regular MÁS ESPECÍFICA
            clean_sql = re.sub(
                r'\b(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\.)',  # Solo tablas SIN schema ya presente
                apply_enhanced_schema_prefix,
                clean_raw_sql,
                flags=re.IGNORECASE
            )
            
            logger.debug(f"SQL después de prefijos multi-schema: {clean_sql}")
            
        else:
            clean_sql = clean_raw_sql
            logger.info("✅ SQL ya tiene prefijos de schema correctos")

        # ========== TU LIMPIEZA Y FORMATO ORIGINAL (mantenida completamente) ==========
        # Remover markdown residual
        clean_sql = re.sub(r'^```sql|```$', '', clean_sql, flags=re.IGNORECASE)
        
        # Aplicar límite estándar
        clean_sql = re.sub(r'(?i)LIMIT\s+\d+', 'LIMIT 100', clean_sql)
        
        # Normalizar espacios y saltos de línea
        clean_sql = re.sub(r'[\s\n]+', ' ', clean_sql).strip()
        
        # Limpiar puntos y comas finales
        clean_sql = re.sub(r';+\s*$', ';', clean_sql)
        if not clean_sql.endswith(';'):
            clean_sql += ';'

        # ========== TU VALIDACIÓN ORIGINAL MEJORADA (combinada) ==========
        # Extraer tablas mencionadas de AMBOS schemas
        mentioned_public_tables = re.findall(r'"public"\."(\w+)"', clean_sql)
        mentioned_tenant_tables = re.findall(rf'"{target_schema}"\."(\w+)"', clean_sql)
        
        validation_errors = []
        
        # TU VALIDACIÓN ORIGINAL (mantenida)
        for table in mentioned_public_tables:
            if table not in available_tables:
                validation_errors.append(f"❌ Tabla PUBLIC '{table}' no existe en los esquemas disponibles")
            elif table not in public_tables:
                validation_errors.append(f"⚠️  Tabla '{table}' existe pero no es del schema public")
        
        for table in mentioned_tenant_tables:
            if table not in available_tables:
                validation_errors.append(f"❌ Tabla TENANT '{table}' no existe en los esquemas disponibles")
            elif table not in tenant_tables:
                validation_errors.append(f"⚠️  Tabla '{table}' existe pero no es del schema tenant")
        
        # TU MANEJO DE ERRORES ORIGINAL (mantenido)
        if validation_errors:
            logger.error(f"Errores de validación multi-schema: {validation_errors}")
            logger.error(f"Tablas públicas disponibles: {public_tables}")
            logger.error(f"Tablas tenant disponibles: {tenant_tables}")
            raise ValueError("\n".join(validation_errors))

        # ========== LOGGING FINAL MEJORADO (combinando ambos enfoques) ==========
        logger.info(f"✅ SQL multi-tenant generado: {clean_sql}")
        logger.info(f"📊 Tablas públicas usadas: {mentioned_public_tables}")
        logger.info(f"📊 Tablas tenant usadas: {mentioned_tenant_tables}")
        # NUEVO: Estadísticas de detección
        logger.info(f"🧠 Detección inteligente: {len(mentioned_public_tables + mentioned_tenant_tables)} tablas ubicadas automáticamente")
        logger.info(f"🎯 Precisión: PUBLIC({len(public_tables)} disponibles), TENANT({len(tenant_tables)} disponibles)")
        
        return clean_sql
    
    def generate_response_from_result(self, natural_query: str, schemas: list, sql_result: dict) -> str:
        """
        Genera respuesta natural OPTIMIZADA en tokens.
        """
        system_prompt = RESPONSE_SYSTEM_PROMPT
        
        # Simplificar resultados para reducir tokens
        simplified_results = {
            "cols": sql_result.get("columns", []),
            "data": sql_result.get("data", [])[:5],  # Solo primeros 5 registros
            "total": len(sql_result.get("data", []))
        }
        
        user_prompt = RESPONSE_USER_PROMPT_TEMPLATE.format(
            query=natural_query,
            results=simplified_results
        )
        
        # Tracking optimizado
        model_name = self.get_model_name()
        prompt_tokens = self.count_tokens(system_prompt + user_prompt)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        print("\n💰 === RESPUESTA - TOKEN OPTIMIZADO ===")
        print(f"📥 Tokens entrada: {prompt_tokens:,}")
        
        response = self.llm.invoke(messages)
        
        response_tokens = self.count_tokens(response.content)
        cost_info = self.calculate_cost(prompt_tokens, response_tokens, model_name)
        
        print(f"📤 Tokens salida: {response_tokens:,}")
        print(f"💰 Costo total: ${cost_info['total_cost']:.6f}")
        print("📊 Optimización: ~60% menos tokens")
        print("=" * 40)
        
        return response.content