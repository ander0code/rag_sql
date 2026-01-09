# Recuperador de schema: selecciona tablas relevantes para cada query

import json
import logging
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import settings

logger = logging.getLogger(__name__)

# Usar configuración centralizada
CACHE_DIR = settings.cache_path


# Selecciona tablas relevantes usando LLM
class SchemaRetriever:
    def __init__(self, llm, schemas: Optional[list] = None):
        self.llm = llm
        self.schemas = schemas or []
        if self.schemas:
            logger.info(f"SchemaRetriever: {len(self.schemas)} tablas cargadas")

    # Carga schemas desde archivo JSON
    @classmethod
    def from_file(cls, llm, filename: str = "discovered_schemas.json"):
        path = CACHE_DIR / filename
        if not path.exists():
            logger.warning(f"No existe: {path}")
            return cls(llm, [])

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(llm, data.get("schemas", []))

    # Carga schemas desde scanner ya escaneado
    @classmethod
    def from_scanner(cls, llm, scanner):
        all_tables = []
        for schema, tables in scanner.schemas_data.items():
            all_tables.extend(tables)
        return cls(llm, all_tables)

    def get_relevant(self, query: str, target_schema: Optional[str] = None) -> list:
        if not self.schemas:
            logger.error("No hay schemas cargados")
            return []

        candidates = self.schemas
        if target_schema:
            candidates = [
                s for s in self.schemas if s["metadata"].get("schema") == target_schema
            ]
            if not candidates:
                logger.warning(
                    f"No hay tablas en schema '{target_schema}', usando todas"
                )
                candidates = self.schemas

        # Si hay pocas tablas, usar todas
        if len(candidates) <= 3:
            return candidates

        tables_info = [
            {
                "table": s["metadata"]["table_name"],
                "schema": s["metadata"].get("schema", "public"),
                "cols": s["metadata"].get("columns", [])[:5],
            }
            for s in candidates
        ]

        prompt = f"""Eres experto en seleccionar tablas para consultas SQL.

QUERY DEL USUARIO: {query}

TABLAS DISPONIBLES:
{json.dumps(tables_info, ensure_ascii=False, indent=2)}

REGLAS:
1. Selecciona SOLO las tablas necesarias (mínimo posible)
2. Incluye tablas relacionadas si se necesitan JOINs
3. Prioriza tablas que contienen los datos solicitados directamente
4. Máximo 4 tablas por consulta

Responde SOLO con JSON: {{"tables": ["tabla1", "tabla2"]}}"""

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content="Experto SQL. Solo JSON."),
                    HumanMessage(content=prompt),
                ]
            )
            clean = response.content.replace("```json", "").replace("```", "").strip()
            names = json.loads(clean).get("tables", [])
            logger.info(f"Seleccionadas: {names}")

            selected = [s for s in candidates if s["metadata"]["table_name"] in names]
            return selected if selected else self._fallback(query, candidates)
        except Exception as e:
            logger.warning(f"LLM falló: {e}")
            return self._fallback(query, candidates)

    async def aget_relevant(
        self, query: str, top_k: int = 5, target_schema: str = None
    ) -> list:
        """Versión asíncrona de get_relevant"""
        candidates = [
            s
            for s in self.schemas
            if not target_schema or s["metadata"].get("schema") == target_schema
        ][:top_k]

        if not candidates:
            return []

        if len(candidates) == 1:
            return self.expand(candidates)

        tables_info = [
            {
                "table": s["metadata"]["table_name"],
                "schema": s["metadata"].get("schema", "public"),
                "cols": s["metadata"].get("columns", [])[:5],
            }
            for s in candidates
        ]

        prompt = f"""Eres experto en seleccionar tablas para consultas SQL.

QUERY DEL USUARIO: {query}

TABLAS DISPONIBLES:
{json.dumps(tables_info, ensure_ascii=False, indent=2)}

REGLAS:
1. Selecciona SOLO las tablas necesarias (mínimo posible)
2. Incluye tablas relacionadas si se necesitan JOINs
3. Prioriza tablas que contienen los datos solicitados directamente
4. Máximo 4 tablas por consulta

Responde SOLO con JSON: {{"tables": ["tabla1", "tabla2"]}}"""

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content="Experto SQL. Solo JSON."),
                    HumanMessage(content=prompt),
                ]
            )
            clean = response.content.replace("```json", "").replace("```", "").strip()
            names = json.loads(clean).get("tables", [])
            logger.info(f"Seleccionadas (async): {names}")

            selected = [s for s in candidates if s["metadata"]["table_name"] in names]
            return selected if selected else self._fallback(query, candidates)
        except Exception as e:
            logger.warning(f"LLM async falló: {e}")
            return self._fallback(query, candidates)

    def _fallback(self, query: str, candidates: list) -> list:
        q = query.lower()
        for s in candidates:
            name = s["metadata"]["table_name"]
            if name in q or name[:-1] in q:
                return [s]

        return [candidates[0]] if candidates else []

    def get_by_name(self, name: str):
        return next(
            (s for s in self.schemas if s["metadata"]["table_name"] == name), None
        )

    def expand(self, schemas: list) -> list:
        result = {s["metadata"]["table_name"]: s for s in schemas}
        for s in schemas:
            for rel in s["metadata"].get("related_tables", []):
                if rel not in result:
                    found = self.get_by_name(rel)
                    if found:
                        result[rel] = found
        return list(result.values())

    def get_available_schemas(self) -> list:
        return list(set(s["metadata"].get("schema", "public") for s in self.schemas))
