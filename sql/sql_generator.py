from utils.prompts import (
    SQL_SYSTEM_PROMPT,
    SQL_USER_PROMPT_TEMPLATE, 
    RESPONSE_SYSTEM_PROMPT, 
    RESPONSE_USER_PROMPT_TEMPLATE
)

import json
import re
import logging
from langchain.schema import HumanMessage, SystemMessage
import tiktoken
from collections import defaultdict, deque

from utils.clients import get_deepseek_llm

logger = logging.getLogger(__name__)

class SQLGenerator:
    """
    Clase para generar consultas SQL a partir de lenguaje natural.
    
    Funcionalidades:
    - Construcción de prompts estructurados
    - Generación de SQL usando LLMs
    - Post-procesamiento y validación de consultas
    """
    def __init__(self):
        """Inicializa modelo LLM y tokenizer."""
        self.llm = get_deepseek_llm()
        logger.info("SQLGenerator inicializado")

    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Cuenta tokens para un texto dado usando el modelo especificado"""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base") 
        return len(encoding.encode(text))

    def generate_sql_and_response(self, natural_query: str, schemas: list, sql_result: dict = None) -> str:
        """
        Pipeline completo para generación de SQL.
        
        Pasos:
        1. Formatear esquemas a JSON estructurado
        2. Construir prompts de sistema y usuario
        3. Generar SQL con LLM
        4. Validar y limpiar resultado
        """
        formatted_schemas = []
        for s in schemas:
            meta = s["metadata"]
            formatted_meta = {
                "tbl": meta.get("table_name"),
                "cols": [col.split(" (")[0] for col in meta.get("columns", [])],
                "rels": [rel["description"].split("->")[-1] for rel in meta.get("relationships", [])]
            }
            formatted_schemas.append(json.dumps(formatted_meta, separators=(',', ':')))
        
        system_prompt = SQL_SYSTEM_PROMPT
        user_prompt = SQL_USER_PROMPT_TEMPLATE.format(
            schemas="\n".join(formatted_schemas),
            query=natural_query
        )
        
        print("----- Prompt Completo para SQL -----")
        print(system_prompt)
        print(user_prompt)
        print("----- Fin del Prompt -----")
        prompt_tokens = self.count_tokens(system_prompt + user_prompt)
        print(f"[DEBUG] Tokens en prompt: {prompt_tokens}")


        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = self.llm.invoke(messages)

        response_tokens = self.count_tokens(response.content)
        logger.debug(f"Tokens en respuesta: {response_tokens}")
        
        return self._postprocess_sql(response.content, schemas)
    
    def _postprocess_sql(self, raw_sql: str, schemas: list) -> str:
        """
        Limpia y valida la SQL generada:
        
        - Elimina formato markdown ```sql
        - Verifica relaciones entre tablas
        - Añade prefijos de esquema (tenant_transactions) si es necesario
        """
        clean_raw_sql = re.sub(r'^```sql|```$', '', raw_sql, flags=re.IGNORECASE)
        schema_prefix = "tenant_transactions"
        
        has_schema_prefix = re.search(rf'"{schema_prefix}"\."[^"]+"', clean_raw_sql) is not None

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
                if 'varchar' in col_type or 'text' in col_type:
                    semantic_tags[table].append(f"texto:{col_name}")
                if 'int' in col_type or 'numeric' in col_type:
                    semantic_tags[table].append(f"número:{col_name}")
                for enum_val in meta.get("enums", {}).get(col_name, []):
                    semantic_tags[table].append(f"valor:{enum_val}")
            
            for rel in meta.get("relationships", []):
                if "->" in rel["description"]:
                    source, target = rel["description"].split("->", 1)
                    src_col = source.strip().split(".")[-1]  
                    target_table = target.split(".")[0].strip() 
                    relation_graph[table].append((src_col, target_table))

        # 1. Extraer las referencias de esquema.tabla
        schema_table_refs = []
        if has_schema_prefix:
            schema_table_refs = re.findall(rf'"{schema_prefix}"\."([^"]+)"', clean_raw_sql)
        
        col_refs = []
        all_refs = re.findall(r'"([^"]+)"\."([^"]+)"', clean_raw_sql)
        
        for first, second in all_refs:

            if first == schema_prefix:
                continue

            if second in [col.split(" (")[0] for schema in schemas 
                        for col in schema["metadata"].get("columns", [])]:
                col_refs.append((first, second))
        
        used_columns = col_refs
        errors = []
        warnings = []
        used_tables = set(schema_table_refs)
        
        for table, col in used_columns:

            if table in available_tables or table in schema_table_refs:

                real_table = table
                if table in schema_table_refs:

                    alias_match = re.search(rf'"{schema_prefix}"\."({table})"\s+AS\s+"([^"]+)"', clean_raw_sql)
                    if alias_match:
                        real_table = alias_match.group(1)
                
                possible_tables = column_tables.get(col, set())
                
                if not possible_tables:
                    errors.append(f"🚨 Columna '{col}' no existe en esquemas")
                elif real_table not in possible_tables:
                    errors.append(f"🚨 Columna '{col}' solo existe en: {', '.join(possible_tables)}")
                else:
                    used_tables.add(real_table)
                    
            else:
                errors.append(f"🚨 Tabla o alias '{table}' no existe en los esquemas")

        if errors:
            error_msg = "Errores de validación críticos:\n" + "\n".join(errors)
            if warnings:
                error_msg += "\n\nAdvertencias:\n" + "\n".join(warnings)
            error_msg += f"\n\nConsulta Original:\n{raw_sql}"
            raise ValueError(error_msg)

        if has_schema_prefix:
            clean_sql = clean_raw_sql
        else:
            clean_sql = re.sub(
                r'\b(FROM|JOIN)\s+"?(\w+)"?',
                lambda m: f'{m.group(1)} "{schema_prefix}"."{m.group(2)}"',
                clean_raw_sql,
                flags=re.IGNORECASE
            )
            
            clean_sql = re.sub(
                r'"(\w+)"\.(\w+)',
                lambda m: f'"{schema_prefix}"."{m.group(1)}"."{m.group(2)}"', 
                clean_sql
            )
        
        clean_sql = re.sub(r'^```sql|```$', '', clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r'(?i)LIMIT\s+\d+', 'LIMIT 100', clean_sql)
        clean_sql = re.sub(r'[\s\n]+', ' ', clean_sql).strip()
        clean_sql = re.sub(r';+\s*$', ';', clean_sql)

        parsed_tables = set(re.findall(rf'"{schema_prefix}"\."(\w+)"', clean_sql))
        required_tables = used_tables.union(parsed_tables)
        
        def find_required_joins(start_tables):
            visited = set(start_tables)
            join_path = []
            for table in start_tables:
                queue = deque([(table, [])])
                while queue:
                    current_table, path = queue.popleft()
                    for src_col, rel_table in relation_graph.get(current_table, []):
                        if rel_table not in visited:
                            visited.add(rel_table)
                            new_path = path + [rel_table]
                            if rel_table in required_tables:
                                join_path.extend(new_path)
                            queue.append((rel_table, new_path))
            return join_path
        
        missing_joins = find_required_joins(parsed_tables)
        
        for join_table in missing_joins:
            if f'"{schema_prefix}"."{join_table}"' not in clean_sql:
                errors.append(f"🚨 JOIN faltante con {join_table}")
        
        if errors:
            raise ValueError("\n".join(errors))

        print(f"[DEBUG] SQL final: {clean_sql}")
        return clean_sql
    
    def generate_response_from_result(self, natural_query: str, schemas: list, sql_result: dict) -> str:
        """
        Genera respuesta natural en español a partir de resultados SQL.
        
        Pasos:
        1. Formatea esquemas para contexto del LLM
        2. Construye prompt estructurado
        3. Genera respuesta natural con LLM
        """
        system_prompt = RESPONSE_SYSTEM_PROMPT
        user_prompt = RESPONSE_USER_PROMPT_TEMPLATE.format(
            query=natural_query,
            results=sql_result
        )
    
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content