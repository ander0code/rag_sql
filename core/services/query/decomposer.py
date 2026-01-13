# QueryDecomposer: Divide consultas complejas en sub-consultas ejecutables

import re
import logging
from typing import List, Tuple
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Patrones que indican consultas múltiples
MULTI_QUERY_PATTERNS = [
    r"\by\b.*\b(dame|muestra|lista|dime)\b",
    r"\b(además|también|asimismo)\b",
    r"\b(primero|segundo|luego|después)\b",
    r"\bde cada\b",
    r"\bpor cada\b",
]

DECOMPOSE_PROMPT = """Analiza si esta consulta requiere múltiples operaciones SQL separadas.

REGLAS:
1. Si pide datos ANIDADOS (ej: "X y los Y de cada X"), DIVIDE en consultas separadas
2. Si usa "y" para pedir dos cosas diferentes, DIVIDE
3. Máximo 3 sub-consultas (prioriza las más importantes)
4. Si es consulta simple, devuélvela igual
5. Cada sub-consulta debe ser independiente y ejecutable

FORMATO DE RESPUESTA (estricto):
- Simple: SIMPLE|consulta
- Múltiple: MULTIPLE|consulta1|consulta2|consulta3

EJEMPLOS:
- "cuantos usuarios hay" → SIMPLE|cuantos usuarios hay
- "10 inmobiliarias con más proyectos y sus proyectos" 
  → MULTIPLE|Las 10 inmobiliarias con más proyectos|Los proyectos de las principales inmobiliarias
- "ventas por mes y productos más vendidos"
  → MULTIPLE|Total de ventas por mes|Productos más vendidos

Responde SOLO con el formato indicado, sin explicaciones."""


class QueryDecomposer:
    """Divide consultas complejas en sub-consultas ejecutables."""

    def __init__(self, llm):
        self.llm = llm
        self._patterns = [re.compile(p, re.IGNORECASE) for p in MULTI_QUERY_PATTERNS]

    def _might_be_complex(self, query: str) -> bool:
        """Detección rápida sin LLM para evitar llamadas innecesarias."""
        # Si es muy corta, probablemente es simple
        if len(query.split()) < 8:
            return False

        # Buscar patrones que indican complejidad
        for pattern in self._patterns:
            if pattern.search(query):
                return True

        return False

    def decompose(self, query: str) -> Tuple[bool, List[str]]:
        """
        Divide la consulta si es compleja.

        Returns:
            (is_multiple, [sub_queries])
            - Si es simple: (False, [query])
            - Si es múltiple: (True, [query1, query2, ...])
        """
        # Optimización: verificar primero con patrones simples
        if not self._might_be_complex(query):
            return False, [query]

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=DECOMPOSE_PROMPT),
                    HumanMessage(content=f"Consulta: {query}"),
                ]
            )

            result = response.content.strip()

            if result.startswith("SIMPLE|"):
                return False, [result[7:].strip()]

            if result.startswith("MULTIPLE|"):
                parts = result[9:].split("|")
                sub_queries = [p.strip() for p in parts if p.strip()]

                if len(sub_queries) > 3:
                    sub_queries = sub_queries[:3]

                logger.info(f"Query descompuesta en {len(sub_queries)} partes")
                return True, sub_queries

            # Si el formato no es válido, tratar como simple
            logger.warning(f"Formato decomposer inválido: {result[:50]}...")
            return False, [query]

        except Exception as e:
            logger.warning(f"Error en decomposer: {e}")
            return False, [query]
