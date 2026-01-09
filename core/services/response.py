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

RESPONSE_SYSTEM = """Eres un asistente amigable que responde consultas sobre bases de datos.

REGLAS DE FORMATO:
1. Responde de forma clara, natural y amigable en español
2. Organiza los datos con viñetas (•) o listas numeradas
3. Incluye el total cuando sea relevante: "Se encontraron X resultados"
4. Si hay >10 resultados, muestra los primeros 10 y menciona el total
5. NO muestres IDs, UUIDs, timestamps ni campos técnicos
6. Redondea números decimales a 2 cifras

CUANDO HAY RESULTADOS:
• Resume primero: "Encontré X registros que coinciden"
• Lista los datos de forma clara
• Si es un conteo, di directamente el número

CUANDO NO HAY RESULTADOS:
• NO digas "no existe en la base de datos"
• Sé amable: "No encontré registros con esas características"
• Sugiere alternativas si es posible

EJEMPLOS BUENOS:
✓ "Hay 85 equipos registrados en el sistema."
✓ "Encontré 3 árbitros: • Juan Pérez • María García • Carlos López"
✓ "El total de ventas del mes fue $15,250.00"

EJEMPLOS MALOS (evitar):
✗ "No existe en la base de datos"
✗ "Query returned 0 rows"
✗ "Error: sin resultados"
✗ "ID: 123, UUID: abc-def..." """

RESPONSE_USER = """PREGUNTA: {query}
DATOS ({total} resultados): {results}

Responde de forma natural y útil:"""


# Genera respuestas en lenguaje natural usando LLM
class ResponseGenerator:
    def __init__(self, llm):
        self.llm = llm

    def generate(self, query: str, result: dict) -> str:
        filtered = self._filter_technical_fields(result)
        total = len(result.get("data", []))

        simplified = {
            "columns": filtered.get("columns", []),
            "data": filtered.get("data", [])[:10],
            "total": total,
        }

        response = self.llm.invoke(
            [
                SystemMessage(content=RESPONSE_SYSTEM),
                HumanMessage(
                    content=RESPONSE_USER.format(
                        query=query, results=simplified, total=total
                    )
                ),
            ]
        )

        return response.content

    async def agenerate(self, query: str, result: dict) -> str:
        """Versión asíncrona de generate"""
        filtered = self._filter_technical_fields(result)
        total = len(result.get("data", []))

        simplified = {
            "columns": filtered.get("columns", []),
            "data": filtered.get("data", [])[:10],
            "total": total,
        }

        response = await self.llm.ainvoke(
            [
                SystemMessage(content=RESPONSE_SYSTEM),
                HumanMessage(
                    content=RESPONSE_USER.format(
                        query=query, results=simplified, total=total
                    )
                ),
            ]
        )

        return response.content

    async def astream(self, query: str, result: dict):
        """Stream asíncrono de la respuesta"""
        filtered = self._filter_technical_fields(result)
        total = len(result.get("data", []))

        simplified = {
            "columns": filtered.get("columns", []),
            "data": filtered.get("data", [])[:10],
            "total": total,
        }

        messages = [
            SystemMessage(content=RESPONSE_SYSTEM),
            HumanMessage(
                content=RESPONSE_USER.format(
                    query=query, results=simplified, total=total
                )
            ),
        ]

        async for token in self.llm.astream(messages):
            yield token

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
