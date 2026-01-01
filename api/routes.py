import time
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager

from application.pipeline import Pipeline
from infrastructure.config.settings import settings
from infrastructure.cache.redis_client import get_redis_client
from core.memory.session_manager import get_session_manager
from core.security.rate_limiter import get_rate_limiter
from core.security.prompt_guard import get_prompt_guard
from core.security.input_sanitizer import get_sanitizer
from core.security.audit_logger import get_audit_logger
from core.security.llm_throttler import get_llm_throttler
from utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Componentes globales inicializados en lifespan
pipeline: Pipeline = None
session_manager = None
rate_limiter = None
prompt_guard = None
sanitizer = None
audit_logger = None
llm_throttler = None


# Inicializa componentes al arrancar la API
@asynccontextmanager
async def lifespan(app: FastAPI):
    global \
        pipeline, \
        session_manager, \
        rate_limiter, \
        prompt_guard, \
        sanitizer, \
        audit_logger
    logger.info("Iniciando RAG-SQL API...")
    start = time.time()

    global llm_throttler

    rate_limiter = get_rate_limiter()
    prompt_guard = get_prompt_guard()
    sanitizer = get_sanitizer()
    audit_logger = get_audit_logger()
    llm_throttler = get_llm_throttler()

    redis = get_redis_client()
    if redis.is_connected():
        session_manager = get_session_manager()
        logger.info("\u2705 Redis conectado")
    else:
        logger.warning("\u26a0\ufe0f Redis no disponible, sesiones deshabilitadas")

    pipeline = Pipeline()
    logger.info(f"\u2705 Pipeline listo ({time.time() - start:.1f}s)")
    logger.info(
        "\ud83d\udee1\ufe0f Seguridad: Rate Limiter, Prompt Guard, LLM Throttler (max 5) activos"
    )
    yield
    logger.info("API detenida")


app = FastAPI(
    title="RAG-SQL API",
    description="Consulta tu base de datos en lenguaje natural con memoria conversacional",
    version="2.1.0",
    lifespan=lifespan,
)


# Modelo de entrada para consultas
class QueryRequest(BaseModel):
    query: str = Field(..., description="Consulta en lenguaje natural", max_length=500)
    session_id: Optional[str] = Field(None, description="ID de sesión para memoria")
    target_schema: Optional[str] = Field(None, description="Schema (opcional)")


# Modelo de respuesta para consultas
class QueryResponse(BaseModel):
    query: str
    result: str
    session_id: Optional[str] = None
    time_seconds: float
    tokens_used: Optional[int] = None
    needs_clarification: bool = False
    clarification: Optional[dict] = None


# Modelo de respuesta para info de la DB
class InfoResponse(BaseModel):
    schemas: list
    total_tables: int
    single_schema: bool
    debug_mode: bool
    redis_connected: bool


# Obtiene IP real del cliente (soporta proxies)
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# GET / - Estado básico de la API
@app.get("/")
async def root():
    redis = get_redis_client()
    return {
        "status": "ok",
        "message": "RAG-SQL Chatbot API",
        "version": "2.1.0",
        "security": ["rate_limiter", "prompt_guard", "sql_validator"],
        "debug": settings.debug,
        "redis": redis.is_connected(),
    }


# GET /health - Estado detallado para monitoreo
@app.get("/health")
async def health():
    redis = get_redis_client()
    throttle_status = llm_throttler.get_status() if llm_throttler else {}
    return {
        "status": "healthy",
        "pipeline_ready": pipeline is not None,
        "redis_connected": redis.is_connected(),
        "llm_throttler": throttle_status,
    }


# GET /info - Info de schemas y tablas disponibles
@app.get("/info", response_model=InfoResponse)
async def get_info():
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline no inicializado")
    redis = get_redis_client()
    info = pipeline.get_info()
    return InfoResponse(
        schemas=info["schemas"],
        total_tables=info["total_tables"],
        single_schema=info["single_schema"],
        debug_mode=settings.debug,
        redis_connected=redis.is_connected(),
    )


# POST /query - Ejecuta consulta en lenguaje natural
@app.post("/query", response_model=QueryResponse)
async def query_database(request: QueryRequest, req: Request):
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline no inicializado")

    client_ip = get_client_ip(req)

    # Rate limiting
    allowed, remaining, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        audit_logger.log_rate_limit(client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit alcanzado. Intenta en {retry_after} segundos.",
            headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
        )

    # Sanitizar input
    query = sanitizer.sanitize_query(request.query)
    if not query:
        raise HTTPException(status_code=400, detail="Query vacía o inválida")

    session_id = sanitizer.sanitize_session_id(request.session_id or "")

    # Verificar prompt injection
    is_safe, reason = prompt_guard.check(query)
    if not is_safe:
        audit_logger.log_prompt_injection(session_id, client_ip, query)
        raise HTTPException(
            status_code=400, detail="Consulta no permitida por políticas de seguridad"
        )

    # Obtener contexto de sesión
    context = ""
    if session_manager:
        if not session_id or not session_manager.session_exists(session_id):
            session_id = session_manager.create_session()
        context = session_manager.get_context_string(session_id)

    audit_logger.log_request(session_id, client_ip, query)

    # Si es ambigua, pedir clarificación
    clarification = pipeline.check_ambiguity(query, context)
    if clarification:
        return QueryResponse(
            query=query,
            result=clarification["message"],
            session_id=session_id,
            time_seconds=0.0,
            needs_clarification=True,
            clarification=clarification,
        )

    # Throttle LLM y ejecutar pipeline
    acquired = await llm_throttler.acquire(timeout=60)
    if not acquired:
        raise HTTPException(
            status_code=503,
            detail="Sistema ocupado. Por favor intenta en unos segundos.",
        )

    try:
        start = time.time()
        result, tokens = pipeline.run(query, request.target_schema, context)
        elapsed = time.time() - start
    finally:
        llm_throttler.release()

    # Guardar en historial
    if session_manager and session_id:
        session_manager.add_exchange(session_id, query, result[:500])

    audit_logger.log_response(session_id, result, tokens or 0)

    response = QueryResponse(
        query=query,
        result=result,
        session_id=session_id,
        time_seconds=round(elapsed, 2),
    )

    if settings.debug and tokens:
        response.tokens_used = tokens

    return response


# POST /scan - Re-escanea la base de datos
@app.post("/scan")
async def scan_database():
    global pipeline
    start = time.time()
    pipeline = Pipeline(use_cache=False)
    info = pipeline.get_info()
    return {
        "status": "ok",
        "tables": info["total_tables"],
        "schemas": info["schemas"],
        "time_seconds": round(time.time() - start, 2),
    }


# DELETE /session/{id} - Elimina una sesión
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_manager:
        safe_id = sanitizer.sanitize_session_id(session_id)
        session_manager.delete_session(safe_id)
        return {"status": "ok", "message": "Sesión eliminada"}
    return {"status": "error", "message": "Redis no disponible"}
