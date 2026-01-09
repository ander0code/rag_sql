# Puerto de LLM

from abc import ABC, abstractmethod
from typing import List, Any, AsyncIterator


class LLMPort(ABC):
    """Puerto para acceso a LLM - Interface abstracta"""

    @abstractmethod
    def invoke(self, messages: List[Any]) -> Any:
        """
        Invoca el LLM con mensajes y retorna respuesta (síncrono).

        Args:
            messages: Lista de mensajes (SystemMessage, HumanMessage, etc.)

        Returns:
            Objeto con atributo .content
        """
        pass

    @abstractmethod
    async def ainvoke(self, messages: List[Any]) -> Any:
        """
        Invoca el LLM con mensajes de forma asíncrona.

        Args:
            messages: Lista de mensajes (SystemMessage, HumanMessage, etc.)

        Returns:
            Objeto con atributo .content
        """
        pass

    @abstractmethod
    async def astream(self, messages: List[Any]) -> AsyncIterator[str]:
        """
        Stream de tokens desde el LLM (asíncrono).

        Args:
            messages: Lista de mensajes

        Yields:
            str: Tokens individuales del stream
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Retorna nombre del modelo en uso"""
        pass
