# Mejorador de consultas - Mejora la query del usuario

import logging
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

ENHANCE_PROMPT = """Eres un experto en interpretar consultas de usuarios sobre bases de datos.

TU TAREA: Mejorar la consulta del usuario para que sea clara y precisa.

REGLAS:
1. NO cambies el significado ni la intención
2. Corrige errores ortográficos y gramaticales
3. Agrega signos de interrogación si es pregunta
4. Convierte frases telegráficas en oraciones completas
5. Mantén términos técnicos/nombres propios sin cambios
6. Si la consulta ya es clara, devuélvela igual

EJEMPLOS:
- "dame ventas" → "Muéstrame las ventas"
- "cuanto vendimos ayer" → "¿Cuánto vendimos ayer?"
- "usuarios registrados ultimo mes" → "¿Cuántos usuarios se registraron el último mes?"
- "productos mas vendidos" → "¿Cuáles son los productos más vendidos?"
- "total facturas cliente ABC" → "¿Cuál es el total de facturas del cliente ABC?"
- "listar empleados activos" → "Lista los empleados activos"

SOLO devuelve la consulta mejorada, sin explicaciones ni formato adicional."""


class QueryEnhancer:
    """
    Mejora la query del usuario para hacerla más clara.
    No solo limpia caracteres, sino que reformula para mejor comprensión.
    """

    def __init__(self, llm):
        self.llm = llm

    def enhance(self, query: str, context: str = "") -> str:
        """
        Mejora la query del usuario.

        Args:
            query: Query original del usuario
            context: Contexto de conversación anterior (opcional)

        Returns:
            Query mejorada y clara
        """
        if not query or len(query.strip()) < 3:
            return query

        prompt = ENHANCE_PROMPT
        if context:
            prompt += f"\n\nContexto de conversación anterior:\n{context}"

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content=f"Consulta del usuario: {query}"),
                ]
            )

            enhanced = response.content.strip()

            # Validar que no sea muy diferente (evitar alucinaciones)
            if len(enhanced) > len(query) * 3:
                logger.warning(
                    "QueryEnhancer: Respuesta demasiado larga, usando original"
                )
                return query

            if enhanced and len(enhanced) > 5:
                logger.debug(f"Query mejorada: '{query}' → '{enhanced}'")
                return enhanced

        except Exception as e:
            logger.warning(f"QueryEnhancer error: {e}")

        return query

    async def aenhance(self, query: str, context: str = "") -> str:
        """
        Versión asíncrona de enhance.

        Args:
            query: Query original del usuario
            context: Contexto de conversación anterior (opcional)

        Returns:
            Query mejorada y clara
        """
        if not query or len(query.strip()) < 3:
            return query

        prompt = ENHANCE_PROMPT
        if context:
            prompt += f"\n\nContexto de conversación anterior:\n{context}"

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content=f"Consulta del usuario: {query}"),
                ]
            )

            enhanced = response.content.strip()

            if len(enhanced) > len(query) * 3:
                logger.warning(
                    "QueryEnhancer: Respuesta demasiado larga, usando original"
                )
                return query

            if enhanced and len(enhanced) > 5:
                logger.debug(f"Query mejorada (async): '{query}' → '{enhanced}'")
                return enhanced

        except Exception as e:
            logger.warning(f"QueryEnhancer async error: {e}")

        return query


_query_enhancer: Optional[QueryEnhancer] = None


def get_query_enhancer(llm) -> QueryEnhancer:
    """Obtiene instancia del QueryEnhancer"""
    global _query_enhancer
    if _query_enhancer is None:
        _query_enhancer = QueryEnhancer(llm)
    return _query_enhancer
