# Excepciones personalizadas para RAG-SQL

class RAGSQLError(Exception):
    """Excepción base para RAG-SQL"""

    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


class ValidationError(RAGSQLError):
    """Errores de validación de entrada"""

    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )


class SecurityError(RAGSQLError):
    """Errores de seguridad (injection, rate limit, off-topic)"""

    def __init__(self, message: str, security_type: str):
        super().__init__(
            message=message, code="SECURITY_ERROR", details={"type": security_type}
        )


class RateLimitError(SecurityError):
    """Rate limit excedido"""

    def __init__(self, message: str = "Rate limit excedido. Intenta en un minuto."):
        super().__init__(message=message, security_type="rate_limit")


class PromptInjectionError(SecurityError):
    """Intento de prompt injection detectado"""

    def __init__(self, message: str = "Consulta rechazada por seguridad."):
        super().__init__(message=message, security_type="prompt_injection")


class OffTopicError(SecurityError):
    """Consulta fuera del tema de base de datos"""

    def __init__(
        self, message: str = "Solo puedo ayudarte con consultas sobre la base de datos."
    ):
        super().__init__(message=message, security_type="off_topic")


class DatabaseError(RAGSQLError):
    """Errores de base de datos"""

    def __init__(self, message: str, query: str = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"query": query[:100] if query else None},
        )


class ConnectionError(DatabaseError):
    """Error de conexión a la base de datos"""

    def __init__(self, message: str = "No se pudo conectar a la base de datos."):
        super().__init__(message=message, query=None)


class SQLExecutionError(DatabaseError):
    """Error al ejecutar SQL"""

    def __init__(self, message: str, query: str = None):
        super().__init__(message=message, query=query)


class LLMError(RAGSQLError):
    """Errores del LLM"""

    def __init__(self, message: str, provider: str = None):
        super().__init__(
            message=message, code="LLM_ERROR", details={"provider": provider}
        )


class SchemaError(RAGSQLError):
    """Errores de schema/tablas"""

    def __init__(self, message: str, schema: str = None):
        super().__init__(
            message=message, code="SCHEMA_ERROR", details={"schema": schema}
        )


class SchemaNotFoundError(SchemaError):
    """Schema no encontrado"""

    def __init__(self, schema: str):
        super().__init__(message=f"Schema '{schema}' no encontrado.", schema=schema)


class NoTablesFoundError(SchemaError):
    """No se encontraron tablas relevantes"""

    def __init__(self, message: str = "No se encontraron tablas relevantes."):
        super().__init__(message=message, schema=None)


class CacheError(RAGSQLError):
    """Errores de cache (Redis/Qdrant)"""

    def __init__(self, message: str, cache_type: str = None):
        super().__init__(
            message=message, code="CACHE_ERROR", details={"cache_type": cache_type}
        )


class PipelineError(RAGSQLError):
    """Errores del pipeline de procesamiento"""

    def __init__(self, message: str, step: str = None):
        super().__init__(
            message=message, code="PIPELINE_ERROR", details={"step": step}
        )
