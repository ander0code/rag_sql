# Rutas de consulta - /query, /query/stream

import time
import logging
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from adapters.inbound.dependencies import AppDependencies, get_deps
from utils.metrics import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


# Modelos de transferencia de datos
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Consulta en lenguaje natural")
    target_schema: Optional[str] = Field(
        None, 
        alias="schema",
        description="Schema específico (opcional, solo si hay múltiples schemas)"
    )
    session_id: Optional[str] = Field(
        None,
        description="ID de sesión para contexto conversacional"
    )


class QueryResponse(BaseModel):
    response: Optional[str] = None
    tokens: Optional[int] = None
    cached: bool = False
    error: Optional[str] = None


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    req: Request,
    deps: AppDependencies = Depends(get_deps),
):
    """Ejecuta una consulta en lenguaje natural"""
    pipeline = deps.pipeline
    session_manager = deps.session_manager
    rate_limiter = deps.rate_limiter
    sanitizer = deps.sanitizer
    prompt_guard = deps.prompt_guard
    topic_detector = deps.topic_detector
    output_validator = deps.output_validator
    audit_logger = deps.audit_logger

    # Rate limiting por IP
    client_ip = req.client.host if req.client else "unknown"
    allowed, remaining = rate_limiter.check(client_ip)
    if not allowed:
        audit_logger.log_security_event(
            "rate_limit", "Rate limit excedido", ip=client_ip
        )
        raise HTTPException(429, "Rate limit excedido. Intenta en un minuto.")

    # Sanitizar
    clean_query = sanitizer.sanitize_query(request.query)

    # Verificar prompt injection
    is_safe, reason = prompt_guard.check(clean_query)
    if not is_safe:
        audit_logger.log_security_event(
            "prompt_injection", reason, ip=client_ip, severity="warning"
        )
        get_metrics().record_security_block("prompt_injection")
        return QueryResponse(error=f"Rechazado: {reason}")

    # Verificar que está en el tema (base de datos)
    is_on_topic, topic_reason = topic_detector.check(clean_query)
    if not is_on_topic:
        audit_logger.log_security_event(
            "off_topic", topic_reason, ip=client_ip, severity="info"
        )
        get_metrics().record_security_block("off_topic")
        return QueryResponse(
            error="Solo puedo ayudarte con consultas sobre la base de datos."
        )

    # Contexto de sesión
    context = ""
    if request.session_id:
        context = session_manager.get_context_string(request.session_id)

    # Ejecutar
    start_time = time.time()
    metrics = get_metrics()
    try:
        response, tokens = pipeline.run(clean_query, request.target_schema, context)

        # Validar output
        is_valid, validated_response = output_validator.validate(response)
        if not is_valid:
            response = output_validator.sanitize(response)

        # Registrar métricas
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_query(duration_ms, cached=False)
        metrics.record_request("/query", duration_ms, success=True)

        # Log de auditoría
        audit_logger.log_query(
            query=clean_query,
            ip=client_ip,
            user_id=request.session_id,
            result_status="success",
            tokens_used=tokens,
            duration_ms=duration_ms,
        )

        # Actualizar sesión
        if request.session_id:
            session_manager.add_message(request.session_id, "user", clean_query)
            session_manager.add_message(request.session_id, "assistant", response)

        return QueryResponse(response=response, tokens=tokens)

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_request("/query", duration_ms, success=False)
        logger.error(f"Error: {e}")
        audit_logger.log_error("query_error", str(e), query=clean_query)
        return QueryResponse(error=str(e))


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    req: Request,
    deps: AppDependencies = Depends(get_deps),
):
    """
    Streaming de respuesta con Server-Sent Events (SSE).
    Retorna tokens en tiempo real - ideal para UI tipo ChatGPT.
    """
    pipeline = deps.pipeline
    session_manager = deps.session_manager
    rate_limiter = deps.rate_limiter
    sanitizer = deps.sanitizer
    prompt_guard = deps.prompt_guard
    topic_detector = deps.topic_detector
    audit_logger = deps.audit_logger

    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    allowed, _ = rate_limiter.check(client_ip)
    if not allowed:

        async def error_stream():
            yield 'data: {"error": "Rate limit excedido"}\n\n'

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Sanitizar y validar
    clean_query = sanitizer.sanitize_query(request.query)

    is_safe, reason = prompt_guard.check(clean_query)
    if not is_safe:

        async def error_stream():
            yield f'data: {{"error": "Rechazado: {reason}"}}\n\n'

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    is_on_topic, _ = topic_detector.check(clean_query)
    if not is_on_topic:

        async def error_stream():
            yield 'data: {"error": "Solo consultas de base de datos"}\n\n'

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Contexto
    context = ""
    if request.session_id:
        context = session_manager.get_context_string(request.session_id)

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Genera el stream de respuesta"""
        start_time = time.time()
        full_response = ""

        try:
            if not pipeline.retriever or not pipeline.retriever.schemas:
                yield 'data: {"error": "No hay schemas disponibles"}\n\n'
                return

            # Resolver schema
            schema = request.target_schema
            if not schema and len(pipeline._available_schemas) == 1:
                schema = pipeline._available_schemas[0]

            # Mejorar query
            enhanced = pipeline.query_enhancer.enhance(clean_query, context)
            query = pipeline.query_rewriter.rewrite(enhanced)

            # Obtener tablas
            relevant = pipeline.retriever.get_relevant(query, target_schema=schema)
            if not relevant:
                yield 'data: {"error": "No se encontraron tablas"}\n\n'
                return

            # Generar SQL
            sql = pipeline.sql_gen.generate(query, relevant, schema)

            # Ejecutar
            result = pipeline.executor.execute(sql)
            if "error" in result:
                yield f'data: {{"error": "{result["error"][:100]}"}}\n\n'
                return

            # Stream de respuesta natural
            async for token in pipeline.response_gen.astream(clean_query, result):
                full_response += token
                yield f'data: {{"token": "{token}"}}\n\n'

            # Señal de fin
            duration_ms = (time.time() - start_time) * 1000
            yield f'data: {{"done": true, "duration_ms": {duration_ms:.0f}}}\n\n'

            # Log
            audit_logger.log_query(
                query=clean_query,
                ip=client_ip,
                result_status="success_stream",
                duration_ms=duration_ms,
            )

            # Actualizar sesión
            if request.session_id and full_response:
                session_manager.add_message(request.session_id, "user", clean_query)
                session_manager.add_message(
                    request.session_id, "assistant", full_response
                )

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f'data: {{"error": "{str(e)[:100]}"}}\n\n'

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
