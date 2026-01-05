# Entidades de Session

from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from uuid import uuid4


@dataclass
class Message:
    """Mensaje en conversación"""

    role: str  # 'user' o 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """Sesión de conversación"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    schema: str = "public"

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))

    def get_context(self, last_n: int = 6) -> str:
        """Retorna últimos mensajes como string"""
        recent = self.messages[-last_n:]
        lines = [
            f"{'Usuario' if m.role == 'user' else 'Asistente'}: {m.content[:200]}"
            for m in recent
        ]
        return "\n".join(lines)

    def clear(self):
        self.messages = []
