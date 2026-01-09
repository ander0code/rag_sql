# Core Domain - Entidades de negocio

from core.domain.query import Query, QueryResult
from core.domain.schema import Table, Column, Schema
from core.domain.session import Session, Message
from core.domain.errors import (
    RAGSQLError,
    ValidationError,
    SecurityError,
    RateLimitError,
    PromptInjectionError,
    OffTopicError,
    DatabaseError,
    ConnectionError,
    SQLExecutionError,
    LLMError,
    SchemaError,
    SchemaNotFoundError,
    NoTablesFoundError,
    CacheError,
    PipelineError,
)
from core.domain.responses import (
    APIResponse,
    ErrorDetail,
    QueryData,
    SessionData,
    HealthData,
    InfoData,
    ScanData,
)

__all__ = [
    # Entidades
    "Query",
    "QueryResult",
    "Table",
    "Column",
    "Schema",
    "Session",
    "Message",
    # Errores
    "RAGSQLError",
    "ValidationError",
    "SecurityError",
    "RateLimitError",
    "PromptInjectionError",
    "OffTopicError",
    "DatabaseError",
    "ConnectionError",
    "SQLExecutionError",
    "LLMError",
    "SchemaError",
    "SchemaNotFoundError",
    "NoTablesFoundError",
    "CacheError",
    "PipelineError",
    # Respuestas
    "APIResponse",
    "ErrorDetail",
    "QueryData",
    "SessionData",
    "HealthData",
    "InfoData",
    "ScanData",
]
