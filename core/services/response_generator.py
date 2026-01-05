# Generador de respuestas: convierte resultados SQL en lenguaje natural

import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Campos técnicos a ocultar en respuestas
HIDDEN_FIELDS = {
    "id",
    "uuid",
    "_id",
    "created_at",
    "updated_at",
    "deleted_at",
    "createdat",
    "updatedat",
    "deletedat",
    "mediaid",
    "fotomediaid",
    "firmamediaid",
    "password",
    "hash",
    "token",
    "secret",
}

RESPONSE_SYSTEM = """Eres un asistente que responde consultas de base de datos.
REGLAS:
- Responde de forma clara y natural en español
- NO muestres IDs, UUIDs ni campos técnicos
- Presenta los datos de forma legible
- Si hay muchos resultados, resume los principales
- Usa formato limpio (listas, viñetas)"""

RESPONSE_USER = """PREGUNTA ORIGINAL: {query}
DATOS OBTENIDOS: {results}

Responde de forma natural:"""


# Genera respuestas en lenguaje natural usando LLM
class ResponseGenerator:
    def __init__(self, llm):
        self.llm = llm

    # Genera respuesta natural a partir de resultados SQL
    def generate(self, query: str, result: dict) -> str:
        filtered = self._filter_technical_fields(result)

        simplified = {
            "columns": filtered.get("columns", []),
            "data": filtered.get("data", [])[:10],
            "total": len(result.get("data", [])),
        }

        response = self.llm.invoke(
            [
                SystemMessage(content=RESPONSE_SYSTEM),
                HumanMessage(
                    content=RESPONSE_USER.format(query=query, results=simplified)
                ),
            ]
        )

        return response.content

    # Filtra campos técnicos (IDs, timestamps, etc.)
    def _filter_technical_fields(self, result: dict) -> dict:
        columns = result.get("columns", [])
        data = result.get("data", [])

        if not columns or not data:
            return result

        visible_indices = []
        visible_columns = []

        for i, col in enumerate(columns):
            col_lower = col.lower().replace("_", "").replace("-", "")
            if not any(hidden in col_lower for hidden in HIDDEN_FIELDS):
                visible_indices.append(i)
                visible_columns.append(col)

        filtered_data = []
        for row in data:
            filtered_row = tuple(row[i] for i in visible_indices if i < len(row))
            filtered_data.append(filtered_row)

        return {"columns": visible_columns, "data": filtered_data}
