# Resumidor de contexto: comprime conversaciones largas

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUMMARIZE_THRESHOLD = 8
KEEP_RECENT = 4

SUMMARIZE_PROMPT = """Resume esta conversación en 1-2 oraciones breves.
Incluye: temas discutidos, entidades mencionadas (torneos, equipos, etc.), y decisiones tomadas.

Conversación:
{messages}

Resumen (máximo 100 palabras):"""


# Resume conversaciones largas para mantener contexto eficiente
class ContextSummarizer:
    def __init__(self, llm):
        self.llm = llm

    # Determina si se debe resumir el historial
    def should_summarize(self, message_count: int) -> bool:
        return message_count > SUMMARIZE_THRESHOLD

    # Resume una lista de mensajes en texto breve
    def summarize(self, messages: list) -> Optional[str]:
        if not messages:
            return None

        formatted = []
        for msg in messages:
            role = "Usuario" if msg.get("role") == "user" else "Asistente"
            content = msg.get("content", "")[:150]
            formatted.append(f"{role}: {content}")

        messages_text = "\n".join(formatted)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = self.llm.invoke(
                [
                    SystemMessage(
                        content="Eres un resumidor conciso. Solo responde con el resumen."
                    ),
                    HumanMessage(
                        content=SUMMARIZE_PROMPT.format(messages=messages_text)
                    ),
                ]
            )

            summary = response.content.strip()
            logger.debug(f"Contexto resumido: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.warning(f"Error resumiendo contexto: {e}")
            return None

    # Retorna contexto optimizado: resumen + mensajes recientes
    def get_optimized_context(
        self, messages: list, existing_summary: str = ""
    ) -> tuple:
        if len(messages) <= SUMMARIZE_THRESHOLD:
            context = self._format_context(messages, existing_summary)
            return existing_summary, messages, context

        old_messages = messages[:-KEEP_RECENT]
        recent_messages = messages[-KEEP_RECENT:]

        new_summary = self.summarize(old_messages)

        if new_summary:
            if existing_summary:
                combined_summary = f"{existing_summary} {new_summary}"
                if len(combined_summary) > 300:
                    combined_summary = combined_summary[-300:]
            else:
                combined_summary = new_summary
        else:
            combined_summary = existing_summary

        context = self._format_context(recent_messages, combined_summary)
        return combined_summary, recent_messages, context

    # Formatea el contexto para incluir en prompts
    def _format_context(self, messages: list, summary: str) -> str:
        parts = []

        if summary:
            parts.append(f"[Contexto previo: {summary}]")

        for msg in messages[-6:]:
            role = "Usuario" if msg.get("role") == "user" else "Asistente"
            content = msg.get("content", "")[:200]
            parts.append(f"{role}: {content}")

        return "\n".join(parts) if parts else ""
