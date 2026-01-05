# API Adapter - FastAPI entry point

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager

from adapters.factory import get_pipeline
from adapters.outbound.cache import get_redis_client
from core.services.session_manager import get_session_manager
from core.services.security import get_prompt_guard, get_sanitizer
from core.services.rate_limiter import get_rate_limiter
from core.services.audit_logger import get_audit_logger
from core.services.guardrails import get_topic_detector, get_output_validator
from utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Componentes globales
pipeline = None
session_manager = None
prompt_guard = None
sanitizer = None
rate_limiter = None
audit_logger = None
topic_detector = None
output_validator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa componentes al startup"""
    global pipeline, session_manager, prompt_guard, sanitizer
    global rate_limiter, audit_logger, topic_detector, output_validator
    logger.info("Iniciando RAG-SQL API...")

    pipeline = get_pipeline()
    session_manager = get_session_manager()
    prompt_guard = get_prompt_guard()
    sanitizer = get_sanitizer()
    rate_limiter = get_rate_limiter()
    audit_logger = get_audit_logger()
    topic_detector = get_topic_detector()
    output_validator = get_output_validator()

    logger.info(f"Pipeline listo: {pipeline.get_info()}")
    yield
    logger.info("Cerrando API...")


app = FastAPI(
    title="RAG-SQL API",
    description="Natural Language to SQL with RAG",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# DTOs
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    target_schema: Optional[str] = Field(None, alias="schema")
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    response: Optional[str] = None
    tokens: Optional[int] = None
    cached: bool = False
    error: Optional[str] = None


# Endpoints
@app.get("/")
async def root():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/health")
async def health():
    redis = get_redis_client()
    return {
        "status": "ok",
        "redis": redis.is_connected(),
        "tables": pipeline.get_info()["total_tables"] if pipeline else 0,
    }


@app.get("/info")
async def info():
    if not pipeline:
        raise HTTPException(503, "Pipeline no inicializado")
    return pipeline.get_info()


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, req: Request):
    if not pipeline:
        raise HTTPException(503, "Pipeline no inicializado")

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
        return QueryResponse(error=f"Rechazado: {reason}")

    # Verificar que está en el tema (base de datos)
    is_on_topic, topic_reason = topic_detector.check(clean_query)
    if not is_on_topic:
        audit_logger.log_security_event(
            "off_topic", topic_reason, ip=client_ip, severity="info"
        )
        return QueryResponse(
            error="Solo puedo ayudarte con consultas sobre la base de datos."
        )

    # Contexto de sesión
    context = ""
    if request.session_id:
        context = session_manager.get_context(request.session_id)

    # Ejecutar
    import time

    start_time = time.time()
    try:
        response, tokens = pipeline.run(clean_query, request.target_schema, context)

        # Validar output
        is_valid, validated_response = output_validator.validate(response)
        if not is_valid:
            response = output_validator.sanitize(response)

        # Log de auditoría
        duration_ms = (time.time() - start_time) * 1000
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
        logger.error(f"Error: {e}")
        audit_logger.log_error("query_error", str(e), query=clean_query)
        return QueryResponse(error=str(e))


@app.post("/session")
async def create_session():
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session_manager.delete_session(session_id)
    return {"deleted": True}


@app.post("/scan")
async def scan():
    if not pipeline:
        raise HTTPException(503, "Pipeline no inicializado")
    pipeline._scan_db()
    return {"status": "scanned", "info": pipeline.get_info()}
