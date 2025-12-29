"""Generador de respuestas naturales."""

import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """Genera respuesta clara y concisa en español basada en los resultados SQL."""

RESPONSE_USER = """PREGUNTA: {query}
RESULTADOS: {results}

Responde de forma natural:"""


class ResponseGenerator:
    def __init__(self, llm):
        self.llm = llm
    
    def generate(self, query: str, result: dict) -> str:
        simplified = {
            "columns": result.get("columns", []),
            "data": result.get("data", [])[:5],
            "total": len(result.get("data", []))
        }
        
        response = self.llm.invoke([
            SystemMessage(content=RESPONSE_SYSTEM),
            HumanMessage(content=RESPONSE_USER.format(query=query, results=simplified))
        ])
        
        return response.content
