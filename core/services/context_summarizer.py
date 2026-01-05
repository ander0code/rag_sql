# Context Summarizer - Resume conversaciones largas

import logging
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """Eres un asistente que resume conversaciones sobre consultas a bases de datos.

Resume la siguiente conversación en 2-3 oraciones, manteniendo:
1. El tema principal de la consulta
2. Información clave mencionada (fechas, productos, filtros, etc.)
3. Lo que el usuario quiere lograr

SOLO devuelve el resumen, sin explicaciones adicionales."""


class ContextSummarizer:
    """
    Resume conversaciones largas para mantener contexto sin exceder tokens.
    Se activa cuando la conversación supera cierto umbral.
    """

    def __init__(self, llm, max_messages_before_summary: int = 8):
        self.llm = llm
        self.max_messages = max_messages_before_summary

    def should_summarize(self, messages: List[dict]) -> bool:
        """Determina si es necesario resumir"""
        return len(messages) >= self.max_messages

    def summarize(self, messages: List[dict]) -> str:
        """
        Resume una lista de mensajes en un texto corto.

        Args:
            messages: Lista de mensajes [{role, content}, ...]

        Returns:
            Resumen de la conversación
        """
        if not messages:
            return ""

        # Formatear mensajes para el prompt
        conversation = "\n".join(
            [
                f"{'Usuario' if m.get('role') == 'user' else 'Asistente'}: {m.get('content', '')[:200]}"
                for m in messages
            ]
        )

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=SUMMARIZE_PROMPT),
                    HumanMessage(content=f"Conversación:\n{conversation}"),
                ]
            )

            summary = response.content.strip()
            logger.debug(
                f"Conversación resumida: {len(messages)} mensajes → {len(summary)} chars"
            )
            return summary

        except Exception as e:
            logger.warning(f"ContextSummarizer error: {e}")
            # Fallback: usar últimos mensajes
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: List[dict]) -> str:
        """Resumen simple sin LLM"""
        if not messages:
            return ""

        # Tomar primero y últimos mensajes
        first = messages[0].get("content", "")[:100] if messages else ""
        last = messages[-1].get("content", "")[:100] if messages else ""

        return f"Inicio: {first}... Último: {last}"

    def get_context_with_summary(
        self, messages: List[dict], keep_recent: int = 4
    ) -> str:
        """
        Obtiene contexto óptimo: resumen + mensajes recientes.

        Args:
            messages: Todos los mensajes
            keep_recent: Cuántos mensajes recientes mantener completos

        Returns:
            String con contexto optimizado
        """
        if len(messages) <= keep_recent:
            # No necesita resumen
            return "\n".join(
                [
                    f"{'Usuario' if m.get('role') == 'user' else 'Asistente'}: {m.get('content', '')}"
                    for m in messages
                ]
            )

        # Resumir mensajes antiguos
        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        summary = self.summarize(old_messages)

        recent_text = "\n".join(
            [
                f"{'Usuario' if m.get('role') == 'user' else 'Asistente'}: {m.get('content', '')}"
                for m in recent_messages
            ]
        )

        return f"[Resumen anterior: {summary}]\n\nConversación reciente:\n{recent_text}"


_context_summarizer: Optional[ContextSummarizer] = None


def get_context_summarizer(llm) -> ContextSummarizer:
    """Obtiene instancia del ContextSummarizer"""
    global _context_summarizer
    if _context_summarizer is None:
        _context_summarizer = ContextSummarizer(llm)
    return _context_summarizer
