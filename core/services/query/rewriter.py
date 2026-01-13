# Reescritor de queries: normaliza y mejora consultas del usuario

import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Eres experto en reformular preguntas para consultas de base de datos.

TU TAREA: Mejorar la redacción de la consulta manteniendo TODA la intención original.

REGLAS:
1. NO elimines información ni simplifiques la consulta
2. Corrige errores ortográficos y gramaticales
3. Hazla más clara y estructurada
4. Mantén todos los filtros, cantidades y relaciones mencionadas
5. Si la consulta ya es clara, devuélvela igual

EJEMPLOS:
- "dame 10 empresas con mas ventas y sus productos top"
  → "Lista las 10 empresas con más ventas junto con sus productos más vendidos"
  
- "usuarios activos ultimo mes con compras"
  → "Muestra los usuarios activos del último mes que tienen compras"

Responde SOLO con la consulta reformulada, sin explicaciones."""


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
