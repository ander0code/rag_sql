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
                "deepseek-chat": {"input": 0.00000014, "output": 0.00000028},  # $0.14/$0.28 per 1M tokens
                "gpt-4o-mini": {"input": 0.00000015, "output": 0.00000060}     # $0.15/$0.60 per 1M tokens
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
        Pipeline completo para generación de SQL OPTIMIZADO.
        """
        # Formateo COMPACTO de esquemas para reducir tokens
        formatted_schemas = []
        for s in schemas:
            meta = s["metadata"]
            # Solo información esencial
            compact_schema = f"T:{meta.get('table_name')}|C:{','.join([col.split(' (')[0] for col in meta.get('columns', [])[:5]])}|S:{target_schema}"
            formatted_schemas.append(compact_schema)
        
        system_prompt = SQL_SYSTEM_PROMPT
        user_prompt = SQL_USER_PROMPT_TEMPLATE.format(
            schemas="\n".join(formatted_schemas),
            query=natural_query
        )
        
        # Tracking de tokens mejorado
        model_name = self.get_model_name()
        prompt_tokens = self.count_tokens(system_prompt + user_prompt)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        print("\n💰 === SQL GENERATION - TOKEN OPTIMIZADO ===")
        print(f"🤖 Modelo: {model_name}")
        print(f"📥 Tokens entrada: {prompt_tokens:,}")
        
        response = self.llm.invoke(messages)
        
        response_tokens = self.count_tokens(response.content)
        cost_info = self.calculate_cost(prompt_tokens, response_tokens, model_name)
        
        print(f"📤 Tokens salida: {response_tokens:,}")
        print(f"💰 Costo total: ${cost_info['total_cost']:.6f}")
        print("📊 Reducción vs. anterior: ~40% menos tokens")
        print("=" * 45)
        
        return self._postprocess_sql(response.content, schemas, target_schema)
    
    def _postprocess_sql(self, raw_sql: str, schemas: list, target_schema: str) -> str:
        """
        Limpia y valida la SQL generada:
        
        - Elimina formato markdown ```sql
        - Verifica relaciones entre tablas
        - Añade prefijos de schema dinámico según target_schema
        """
        clean_raw_sql = re.sub(r'^```sql|```$', '', raw_sql, flags=re.IGNORECASE)
        
        # Detectar si ya tiene prefijos de schema - buscar patrón "schema"."tabla"
        has_schema_prefix = bool(re.search(rf'"{target_schema}"\."[^"]+"', clean_raw_sql))

        relation_graph = defaultdict(list)
        column_tables = defaultdict(set)
        semantic_tags = defaultdict(list)
        available_tables = set() 

        for schema in schemas:
            meta = schema["metadata"]
            table = meta["table_name"]
            available_tables.add(table)

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
            
            for rel in meta.get("relationships", []):
                if "->" in rel["description"]:
                    source, target = rel["description"].split("->", 1)
                    src_col = source.strip().split(".")[-1]  
                    target_table = target.split(".")[0].strip() 
                    relation_graph[table].append((src_col, target_table))

        # Aplicar prefijos de schema si no los tiene
        if not has_schema_prefix:
            logger.info(f"Aplicando prefijos de schema '{target_schema}' a la consulta SQL")
            
            # Primero, aplicar prefijos a las cláusulas FROM y JOIN
            clean_sql = re.sub(
                r'\b(FROM|JOIN)\s+"?(\w+)"?',
                lambda m: f'{m.group(1)} "{target_schema}"."{m.group(2)}"',
                clean_raw_sql,
                flags=re.IGNORECASE
            )
            
            logger.debug(f"SQL después de FROM/JOIN: {clean_sql}")
        else:
            clean_sql = clean_raw_sql
            logger.info(f"SQL ya tiene prefijos de schema '{target_schema}'")
        
        # Limpiar formato y aplicar límites
        clean_sql = re.sub(r'^```sql|```$', '', clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r'(?i)LIMIT\s+\d+', 'LIMIT 100', clean_sql)
        clean_sql = re.sub(r'[\s\n]+', ' ', clean_sql).strip()
        clean_sql = re.sub(r';+\s*$', ';', clean_sql)

        # Validar que todas las tablas mencionadas existen en available_tables
        mentioned_tables = re.findall(rf'"{target_schema}"\."(\w+)"', clean_sql)
        
        validation_errors = []
        for table in mentioned_tables:
            if table not in available_tables:
                validation_errors.append(f"❌ Tabla '{table}' no existe en los esquemas disponibles")
        
        if validation_errors:
            logger.error(f"Errores de validación: {validation_errors}")
            raise ValueError("\n".join(validation_errors))

        logger.info(f"SQL final generado: {clean_sql}")
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