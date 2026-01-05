# Gestor de sesiones: maneja historial de conversaciones en Redis

import uuid
import logging
from typing import List
from adapters.outbound.cache import get_redis_client
from config.settings import settings

logger = logging.getLogger(__name__)


# Representa un mensaje en la conversación
class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(data["role"], data["content"])


# Gestiona sesiones de conversación usando Redis
class SessionManager:
    def __init__(self):
        self.redis = get_redis_client()
        self.max_history = settings.max_history

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    # Crea una nueva sesión y retorna su ID
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.redis.set(self._key(session_id), {"messages": []})
        logger.debug(f"Nueva sesión: {session_id}")
        return session_id

    # Obtiene historial de mensajes de una sesión
    def get_history(self, session_id: str) -> List[ChatMessage]:
        data = self.redis.get(self._key(session_id))
        if not data:
            return []
        return [ChatMessage.from_dict(m) for m in data.get("messages", [])]

    # Agrega un mensaje al historial
    def add_message(self, session_id: str, role: str, content: str):
        data = self.redis.get(self._key(session_id))
        if not data:
            data = {"messages": []}

        messages = data.get("messages", [])
        messages.append({"role": role, "content": content})

        # Sliding window: mantener solo últimos N mensajes
        if len(messages) > self.max_history:
            messages = messages[-self.max_history :]

        data["messages"] = messages
        self.redis.set(self._key(session_id), data)

    # Agrega un intercambio completo (pregunta + respuesta)
    def add_exchange(self, session_id: str, user_query: str, assistant_response: str):
        self.add_message(session_id, "user", user_query)
        self.add_message(session_id, "assistant", assistant_response)

    # Retorna historial como string para incluir en prompts
    def get_context_string(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""

        lines = []
        for msg in history[-6:]:
            prefix = "Usuario" if msg.role == "user" else "Asistente"
            lines.append(f"{prefix}: {msg.content[:200]}")

        return "\n".join(lines)

    # Elimina una sesión
    def delete_session(self, session_id: str):
        self.redis.delete(self._key(session_id))
        logger.debug(f"Sesión eliminada: {session_id}")

    # Verifica si una sesión existe
    def session_exists(self, session_id: str) -> bool:
        return self.redis.get(self._key(session_id)) is not None


_session_manager = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
