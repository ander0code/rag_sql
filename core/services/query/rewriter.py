# Reescritor de queries: normaliza y mejora consultas del usuario

import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Eres experto en reformular preguntas para consultas de base de datos.

REGLAS:
1. Si la pregunta pide dos cosas incompatibles (contar Y listar), elige la más específica
2. Simplifica manteniendo la intención original
3. Corrige errores ortográficos si los hay
4. Mantén el idioma original del usuario
5. Si la pregunta ya es clara, devuélvela igual

Responde SOLO con la pregunta reformulada, sin explicaciones."""


# Reescribe queries para mejorar la generación de SQL
class QueryRewriter:
    def __init__(self, llm):
        self.llm = llm

    def rewrite(self, query: str) -> str:
        # Queries cortas no necesitan reescritura
        if len(query.split()) <= 4:
            return query

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=REWRITE_PROMPT),
                    HumanMessage(content=f"Reformula si es necesario: {query}"),
                ]
            )
            rewritten = response.content.strip().strip('"').strip("'")

            if rewritten and len(rewritten) > 3:
                if rewritten.lower() != query.lower():
                    logger.info(f"Query reescrita: '{query}' → '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Error en rewrite: {e}")

        return query
