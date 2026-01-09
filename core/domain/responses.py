# Modelos de respuesta estandarizados para la API

from typing import TYPE_CHECKING, Optional, Generic, TypeVar
from pydantic import BaseModel

if TYPE_CHECKING:
    from core.domain.errors import RAGSQLError

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detalle de error para respuestas"""

    code: str
    message: str
    details: Optional[dict] = None


class APIResponse(BaseModel, Generic[T]):
    """Respuesta estándar de la API"""

    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: T = None) -> "APIResponse[T]":
        """Crea respuesta exitosa"""
        return cls(success=True, data=data)

    @classmethod
    def fail(
        cls, code: str, message: str, details: dict = None
    ) -> "APIResponse[None]":
        """Crea respuesta de error"""
        return cls(
            success=False,
            error=ErrorDetail(code=code, message=message, details=details),
        )

    @classmethod
    def from_exception(cls, exc: "RAGSQLError") -> "APIResponse[None]":
        """Crea respuesta desde excepción RAGSQLError"""
        return cls(
            success=False,
            error=ErrorDetail(
                code=exc.code, message=exc.message, details=exc.details
            ),
        )


# DTOs específicos para cada endpoint


class QueryData(BaseModel):
    """Datos de respuesta de query"""

    response: str
    tokens: Optional[int] = None
    cached: bool = False


class SessionData(BaseModel):
    """Datos de sesión"""

    session_id: str


class HealthData(BaseModel):
    """Datos de health check"""

    status: str
    redis: bool
    tables: int


class InfoData(BaseModel):
    """Datos de información del sistema"""

    schemas: list
    total_tables: int
    single_schema: bool


class ScanData(BaseModel):
    """Datos de escaneo de DB"""

    status: str
    schemas: list
    total_tables: int
