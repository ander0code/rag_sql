"""Generador de SQL."""

import re
import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

SQL_SYSTEM = """Eres experto en PostgreSQL multi-tenant. Genera SQL válido.
REGLAS:
- Usa prefijos de schema: "public"."tabla" o "{schema}"."tabla"
- Solo SELECT, sin modificaciones
- Incluye LIMIT 100"""

SQL_USER = """TABLAS:
{tables}

QUERY: {query}
SCHEMA TENANT: {schema}

Genera SQL:"""


class SQLGenerator:
    def __init__(self, llm):
        self.llm = llm
    
    def generate(self, query: str, schemas: list, target_schema: str) -> str:
        public, tenant = set(), set()
        tables_info = []
        
        for s in schemas:
            name = s["metadata"]["table_name"]
            stype = s["metadata"].get("schema", "tenant")
            cols = [c.split(" (")[0] for c in s["metadata"].get("columns", [])[:5]]
            
            if stype == "public":
                public.add(name)
                tables_info.append(f"public.{name}: {cols}")
            else:
                tenant.add(name)
                tables_info.append(f"{target_schema}.{name}: {cols}")
        
        prompt = SQL_USER.format(
            tables="\n".join(tables_info),
            query=query,
            schema=target_schema
        )
        
        response = self.llm.invoke([
            SystemMessage(content=SQL_SYSTEM),
            HumanMessage(content=prompt)
        ])
        
        return self._clean(response.content, target_schema, public, tenant)
    
    def _clean(self, raw: str, target_schema: str, public: set, tenant: set) -> str:
        # Extraer SQL de markdown
        sql = raw
        if '```' in raw:
            lines = []
            in_block = False
            for line in raw.split('\n'):
                if line.startswith('```sql'):
                    in_block = True
                elif line.startswith('```'):
                    in_block = False
                elif in_block:
                    lines.append(line)
            sql = ' '.join(lines)
        
        if not sql.strip():
            start = raw.upper().find('SELECT')
            if start != -1:
                sql = raw[start:]
        
        # Aplicar prefijos si no existen
        if not re.search(r'"public"\.|"' + target_schema + r'"\.', sql):
            def add_prefix(m):
                table = m.group(2)
                if table in public:
                    return f'{m.group(1)} "public"."{table}"'
                elif table in tenant:
                    return f'{m.group(1)} "{target_schema}"."{table}"'
                return m.group(0)
            
            sql = re.sub(r'\b(FROM|JOIN)\s+([a-zA-Z_]\w*)\b(?!\s*\.)', add_prefix, sql, flags=re.IGNORECASE)
        
        # Limpiar
        sql = re.sub(r'[\s\n]+', ' ', sql).strip()
        sql = re.sub(r'(?i)LIMIT\s+\d+', 'LIMIT 100', sql)
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
