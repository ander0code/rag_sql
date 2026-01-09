# Rutas de administración - /scan, /info

import logging
from fastapi import APIRouter, Depends

from adapters.inbound.dependencies import get_pipeline_dep
from core.services.pipeline import Pipeline
from utils.metrics import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


@router.get("/info")
async def info(pipeline: Pipeline = Depends(get_pipeline_dep)):
    """Información del pipeline y schemas disponibles"""
    return pipeline.get_info()


@router.post("/scan")
async def scan(pipeline: Pipeline = Depends(get_pipeline_dep)):
    """Re-escanea la base de datos para actualizar schemas"""
    pipeline._scan_db()
    get_metrics().set_tables_indexed(pipeline.get_info()["total_tables"])
    return {"status": "scanned", "info": pipeline.get_info()}
