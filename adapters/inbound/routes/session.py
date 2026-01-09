# Rutas de sesión - /session

import logging
from fastapi import APIRouter, Depends

from adapters.inbound.dependencies import AppDependencies, get_deps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("")
async def create_session(deps: AppDependencies = Depends(get_deps)):
    """Crea una nueva sesión de chat"""
    session_id = deps.session_manager.create_session()
    return {"session_id": session_id}


@router.delete("/{session_id}")
async def delete_session(session_id: str, deps: AppDependencies = Depends(get_deps)):
    """Elimina una sesión existente"""
    deps.session_manager.delete_session(session_id)
    return {"deleted": True}
