# Generador SQL: convierte queries en lenguaje natural a SQL

import re
import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

SQL_SYSTEM = """Eres un generador de SQL. Tu respuesta debe ser ÚNICAMENTE código SQL.

CRÍTICO - FORMATO DE RESPUESTA:
- SOLO código SQL, NADA más
- SIN texto explicativo
- SIN markdown (no uses ```)
- SIN comentarios
- La respuesta debe EMPEZAR con SELECT

REGLAS SQL:
1. SOLO SELECT (nunca INSERT, UPDATE, DELETE)
2. Usa schema: "public"."tabla"
3. SIEMPRE incluye LIMIT (máximo 100)
4. NO uses LATERAL ni subconsultas complejas

PATRONES VÁLIDOS:
SELECT col1, col2 FROM "public"."tabla" LIMIT 20
SELECT COUNT(*) FROM "public"."tabla"
SELECT t1.col, t2.col FROM "public"."t1" JOIN "public"."t2" ON t1.id = t2.t1_id LIMIT 20
SELECT col, COUNT(*) as total FROM "public"."t" GROUP BY col ORDER BY total DESC LIMIT 10

PROHIBIDO:
- LATERAL JOIN
- LIMIT dentro de ARRAY_AGG
- Texto antes o después del SQL"""

SQL_USER = """TABLAS: {tables}
SCHEMA: {schema}
PREGUNTA: {query}

Responde SOLO con el SELECT:"""

SQL_RETRY = """El SQL anterior produjo este error:
{error}

TABLAS DISPONIBLES:
{tables}

CONSULTA DEL USUARIO: {query}

Genera un SQL CORREGIDO que evite el error:"""


# Genera SQL a partir de lenguaje natural usando LLM
class SQLGenerator:
    def __init__(self, llm):
        self.llm = llm

    def generate(
        self, query: str, schemas: list, target_schema: str, previous_error: str = None
    ) -> str:
        tables_info = self._build_tables_info(schemas, target_schema)

        if previous_error:
            prompt = SQL_RETRY.format(
                error=previous_error[:300], tables="\n".join(tables_info), query=query
            )
        else:
            prompt = SQL_USER.format(
                tables="\n".join(tables_info), query=query, schema=target_schema
            )

        response = self.llm.invoke(
            [SystemMessage(content=SQL_SYSTEM), HumanMessage(content=prompt)]
        )

        return self._clean(response.content, schemas, target_schema)

    async def agenerate(
        self, query: str, schemas: list, target_schema: str, previous_error: str = None
    ) -> str:
        """Versión asíncrona de generate"""
        tables_info = self._build_tables_info(schemas, target_schema)

        if previous_error:
            prompt = SQL_RETRY.format(
                error=previous_error[:300], tables="\n".join(tables_info), query=query
            )
        else:
            prompt = SQL_USER.format(
                tables="\n".join(tables_info), query=query, schema=target_schema
            )

        response = await self.llm.ainvoke(
            [SystemMessage(content=SQL_SYSTEM), HumanMessage(content=prompt)]
        )

        return self._clean(response.content, schemas, target_schema)

    def _build_tables_info(self, schemas: list, target_schema: str) -> list:
        tables_info = []
        for s in schemas:
            name = s["metadata"]["table_name"]
            schema = s["metadata"].get("schema", "public")
            cols = s["metadata"].get("columns", [])[:8]
            enum_cols = s["metadata"].get("enum_columns", {})

            col_names = [c.split(" (")[0] for c in cols]
            table_info = f'"{schema}"."{name}": columns={col_names}'

            if enum_cols:
                enum_info = [f"{k}=[{', '.join(v[:5])}]" for k, v in enum_cols.items()]
                table_info += f" | enums: {', '.join(enum_info)}"

            tables_info.append(table_info)
        return tables_info

    def _clean(self, raw: str, schemas: list, target_schema: str) -> str:
        sql = raw.strip()

        # Extraer SQL de markdown ```sql ... ```
        if "```" in raw:
            lines = []
            in_block = False
            for line in raw.split("\n"):
                if line.strip().lower().startswith("```sql"):
                    in_block = True
                elif line.strip().startswith("```"):
                    in_block = False
                elif in_block:
                    lines.append(line)
            if lines:
                sql = " ".join(lines).strip()

        # Si no empieza con SELECT, buscar SELECT en el texto
        if not sql.upper().strip().startswith("SELECT"):
            # Buscar el primer SELECT en el texto
            match = re.search(r"\bSELECT\b", sql, re.IGNORECASE)
            if match:
                sql = sql[match.start() :]
            else:
                # No hay SELECT, retornar vacío para que falle la validación
                logger.warning(f"No se encontró SELECT en: {raw[:100]}...")
                return ""

        # Mapa de tablas con sus schemas
        table_schema_map = {
            s["metadata"]["table_name"].lower(): {
                "name": s["metadata"]["table_name"],
                "schema": s["metadata"].get("schema", "public"),
            }
            for s in schemas
        }

        # Corregir nombres de tablas con schema correcto
        def fix_table(match):
            prefix = match.group(1)
            table = match.group(2)
            info = table_schema_map.get(
                table.lower(), {"name": table, "schema": "public"}
            )
            return f'{prefix} "{info["schema"]}"."{info["name"]}"'

        sql = re.sub(
            r'\b(FROM|JOIN)\s+(?:"?\w+"?\.)?([a-zA-Z_]\w*)\b(?!\s*\.)',
            fix_table,
            sql,
            flags=re.IGNORECASE,
        )

        sql = re.sub(r"[\s\n]+", " ", sql).strip()

        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 100"

        if not sql.endswith(";"):
            sql += ";"

        return sql
