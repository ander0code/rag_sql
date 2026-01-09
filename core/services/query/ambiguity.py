# Detector de ambigüedad: analiza si una query necesita clarificación

import logging
from typing import Tuple, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

AMBIGUITY_PROMPT = """Analiza si la siguiente consulta de base de datos es ambigua.

TABLAS DISPONIBLES EN LA BASE DE DATOS:
{tables_info}

REGLAS:
1. Una consulta es CLARA si:
   - Pide datos generales sin filtros (ej: "cuantos registros hay en X")
   - Especifica todos los filtros necesarios
   - Tiene contexto suficiente del historial

2. Una consulta es AMBIGUA si:
   - Menciona una entidad sin especificar cuál (ej: "el registro" sin decir cuál)
   - Pide datos que requieren un filtro no especificado
   - Hace referencia a algo previo sin contexto suficiente

3. Si es ambigua, indica QUÉ TABLA o CAMPO necesita clarificación.
   Solo usa tablas que existen en el schema.

HISTORIAL:
{context}

CONSULTA: {query}

Responde SOLO así:
- Si es clara: CLARA
- Si es ambigua: AMBIGUA|nombre_tabla|pregunta_para_clarificar

Ejemplos:
- CLARA
- AMBIGUA|Torneos|¿De cuál torneo necesitas la información?
- AMBIGUA|Equipos|¿Cuál equipo te interesa?
"""


# Detecta queries ambiguas usando LLM y schema de la DB
class AmbiguityDetector:
    def __init__(self, llm):
        self.llm = llm
        self._tables_info = ""
        self._valid_tables = []

    def set_schema_info(self, tables: List[Dict]):
        self._valid_tables = []
        table_lines = []

        for table in tables:
            name = table.get("table_name", "")
            if name and not name.startswith("_"):
                self._valid_tables.append(name.lower())
                columns = table.get("columns", [])
                col_names = [c.split(" ")[0] for c in columns[:5]]
                table_lines.append(f"- {name}: {', '.join(col_names)}")

        self._tables_info = (
            "\n".join(table_lines) if table_lines else "Schema no disponible"
        )

    def check(self, query: str, context: str = "") -> Tuple[bool, str, str]:
        prompt = AMBIGUITY_PROMPT.format(
            query=query,
            context=context or "Sin historial",
            tables_info=self._tables_info or "Schema general",
        )

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(
                        content="Eres un analizador de consultas SQL. Responde solo con el formato indicado."
                    ),
                    HumanMessage(content=prompt),
                ]
            )

            result = response.content.strip()

            if result.startswith("CLARA"):
                return False, "", ""

            if result.startswith("AMBIGUA"):
                parts = result.split("|")
                if len(parts) >= 3:
                    entity_type = parts[1].strip()
                    question = parts[2].strip()

                    if not self._is_valid_entity(entity_type):
                        logger.debug(
                            f"Entidad '{entity_type}' no existe en schema, ignorando"
                        )
                        return False, "", ""

                    logger.debug(f"Consulta ambigua: {entity_type}")
                    return True, entity_type, question

            return False, "", ""

        except Exception as e:
            logger.warning(f"Error en ambiguity check: {e}")
            return False, "", ""

    def _is_valid_entity(self, entity: str) -> bool:
        if not self._valid_tables:
            return True

        entity_lower = entity.lower()

        for table in self._valid_tables:
            if entity_lower == table or entity_lower in table or table in entity_lower:
                return True

        return False

    def get_valid_tables(self) -> List[str]:
        return self._valid_tables.copy()
