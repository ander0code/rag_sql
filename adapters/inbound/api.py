# Adaptador API - Punto de entrada FastAPI

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from adapters.inbound.dependencies import AppDependencies
from adapters.inbound.routes import (
    query_router,
    health_router,
    session_router,
    admin_router,
)
from core.domain.errors import (
    RAGSQLError,
    SecurityError,
    RateLimitError,
    DatabaseError,
)
from utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el contenedor de dependencias al startup"""
    logger.info("Iniciando RAG-SQL API...")

    deps = AppDependencies.get_instance()
    deps.initialize_all()

    logger.info(f"Pipeline listo: {deps.pipeline.get_info()}")
    yield
    logger.info("Cerrando API...")


app = FastAPI(
    title="RAG-SQL API",
    description="Natural Language to SQL with RAG",
    version="2.0.0",
    lifespan=lifespan,
)

# Configuración de Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Manejadores de excepciones
@app.exception_handler(RAGSQLError)
async def ragsql_exception_handler(request: Request, exc: RAGSQLError):
    """Maneja excepciones personalizadas de RAG-SQL"""
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": exc.to_dict()},
    )


@app.exception_handler(SecurityError)
async def security_exception_handler(request: Request, exc: SecurityError):
    """Maneja errores de seguridad"""
    status_code = 429 if isinstance(exc, RateLimitError) else 403
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": exc.to_dict()},
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Maneja errores de base de datos"""
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": exc.to_dict()},
    )


# Registro de routers
app.include_router(health_router)  # /, /health, /metrics
app.include_router(query_router)  # /query, /query/stream
app.include_router(session_router)  # /session
app.include_router(admin_router)  # /info, /scan

