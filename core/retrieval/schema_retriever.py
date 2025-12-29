"""Recuperador de esquemas dinámico."""

import json
import logging
from pathlib import Path
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "config" / "schemas"


class SchemaRetriever:
    def __init__(self, llm, schemas: Optional[list] = None):
        self.llm = llm
        self.schemas = schemas or []
        if self.schemas:
            logger.info(f"SchemaRetriever: {len(self.schemas)} tablas cargadas")
    
    @classmethod
    def from_file(cls, llm, filename: str = "discovered_schemas.json"):
        """Carga desde archivo JSON."""
        path = CACHE_DIR / filename
        if not path.exists():
            logger.warning(f"No existe: {path}")
            return cls(llm, [])
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(llm, data.get("schemas", []))
    
    @classmethod
    def from_scanner(cls, llm, scanner):
        """Carga desde scanner (ya escaneado)."""
        all_tables = []
        for schema, tables in scanner.schemas_data.items():
            all_tables.extend(tables)
        return cls(llm, all_tables)
    
    def get_relevant(self, query: str, target_schema: Optional[str] = None) -> list:
        """Selecciona tablas relevantes para la query."""
        if not self.schemas:
            logger.error("No hay schemas cargados")
            return []
        
        # Filtrar por schema si se especifica
        candidates = self.schemas
        if target_schema:
            candidates = [s for s in self.schemas if s["metadata"].get("schema") == target_schema]
            if not candidates:
                logger.warning(f"No hay tablas en schema '{target_schema}', usando todas")
                candidates = self.schemas
        
        # Si pocas tablas, usar todas
        if len(candidates) <= 3:
            return candidates
        
        # Usar LLM para seleccionar
        tables_info = [{"table": s["metadata"]["table_name"], 
                        "schema": s["metadata"].get("schema", "public"),
                        "cols": s["metadata"].get("columns", [])[:5]} 
                       for s in candidates]
        
        prompt = f"""Selecciona tablas MÍNIMAS para: {query}
TABLAS: {json.dumps(tables_info, ensure_ascii=False)}
Responde JSON: {{"tables": ["tabla1"]}}"""

        try:
            response = self.llm.invoke([
                SystemMessage(content="Experto SQL. Solo JSON."),
                HumanMessage(content=prompt)
            ])
            clean = response.content.replace('```json', '').replace('```', '').strip()
            names = json.loads(clean).get("tables", [])
            logger.info(f"Seleccionadas: {names}")
            
            selected = [s for s in candidates if s["metadata"]["table_name"] in names]
            return selected if selected else self._fallback(query, candidates)
        except Exception as e:
            logger.warning(f"LLM falló: {e}")
            return self._fallback(query, candidates)

    def _fallback(self, query: str, candidates: list) -> list:
        """Fallback: busca menciones directas."""
        q = query.lower()
        for s in candidates:
            name = s["metadata"]["table_name"]
            if name in q or name[:-1] in q:
                return [s]
        # Retorna la primera
        return [candidates[0]] if candidates else []
    
    def get_by_name(self, name: str):
        return next((s for s in self.schemas if s["metadata"]["table_name"] == name), None)
    
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
        """Lista schemas únicos disponibles."""
        return list(set(s["metadata"].get("schema", "public") for s in self.schemas))
