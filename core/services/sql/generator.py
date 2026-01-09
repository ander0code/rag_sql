# Generador SQL: convierte queries en lenguaje natural a SQL

import re
import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

SQL_SYSTEM = """Eres experto en PostgreSQL. Genera consultas SQL válidas y eficientes.

REGLAS CRÍTICAS:
1. Usa prefijos de schema: "schema"."tabla"
2. SOLO SELECT (consultas de lectura)
3. NO mezcles funciones de agregación (COUNT, SUM, AVG) con columnas sin GROUP BY
4. SIEMPRE incluye LIMIT (máximo 100)
5. Usa alias claros para JOINs (ej: t1, t2 o nombres descriptivos)
6. Prefiere ILIKE para búsquedas de texto (case-insensitive)
7. Para fechas usa: date_column >= CURRENT_DATE - INTERVAL 'N days'

PATRONES COMUNES:
- Contar: SELECT COUNT(*) FROM "schema"."tabla"
- Listar: SELECT col1, col2 FROM "schema"."tabla" LIMIT 20
- Filtrar texto: WHERE col ILIKE '%valor%'
- Agrupar: SELECT col, COUNT(*) FROM tabla GROUP BY col
- Top N: SELECT col, COUNT(*) as total FROM tabla GROUP BY col ORDER BY total DESC LIMIT 10

ERRORES A EVITAR:
- ❌ SELECT nombre, COUNT(*) FROM tabla (falta GROUP BY)
- ❌ SELECT * sin LIMIT
- ❌ Usar = para texto (usar ILIKE)
- ❌ Olvidar comillas en nombres de schema/tabla
- ❌ JOINs sin ON clause"""

SQL_USER = """TABLAS DISPONIBLES:
{tables}

CONSULTA DEL USUARIO: {query}
SCHEMA: {schema}

Genera el SQL:"""

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
        sql = raw

        # Extraer SQL de markdown
        if "```" in raw:
            lines = []
            in_block = False
            for line in raw.split("\n"):
                if line.startswith("```sql") or line.startswith("```SQL"):
                    in_block = True
                elif line.startswith("```"):
                    in_block = False
                elif in_block:
                    lines.append(line)
            if lines:
                sql = " ".join(lines)

        if not sql.strip() or "SELECT" not in sql.upper():
            start = raw.upper().find("SELECT")
            if start != -1:
                sql = raw[start:]

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
