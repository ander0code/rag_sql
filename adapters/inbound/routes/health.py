# Rutas de salud - /health, /metrics

import logging
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from adapters.inbound.dependencies import AppDependencies, get_deps
from adapters.outbound.cache import get_redis_client
from utils.metrics import get_metrics, get_health_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Root endpoint - status básico"""
    return {"status": "ok", "version": "2.0.0"}


@router.get("/health")
async def health(deps: AppDependencies = Depends(get_deps)):
    """Health check básico"""
    redis = get_redis_client()
    metrics = get_metrics()
    metrics.set_tables_indexed(deps.pipeline.get_info()["total_tables"])
    return {
        "status": "ok",
        "redis": redis.is_connected(),
        "tables": deps.pipeline.get_info()["total_tables"],
    }


@router.get("/health/detailed")
async def health_detailed():
    """Health check detallado con métricas del sistema"""
    return get_health_status()


@router.get("/metrics")
async def metrics_json():
    """Métricas en formato JSON"""
    return get_metrics().get_metrics()


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def metrics_prometheus():
    """Métricas en formato Prometheus"""
    return get_metrics().get_prometheus_format()
