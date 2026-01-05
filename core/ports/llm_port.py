# Puerto de LLM

from abc import ABC, abstractmethod
from typing import List, Any


class LLMPort(ABC):
    """Puerto para acceso a LLM - Interface abstracta"""

    @abstractmethod
    def invoke(self, messages: List[Any]) -> Any:
        """
        Invoca el LLM con mensajes y retorna respuesta.

        Args:
            messages: Lista de mensajes (SystemMessage, HumanMessage, etc.)

        Returns:
            Objeto con atributo .content
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Retorna nombre del modelo en uso"""
        pass
