# Paquete de rutas - Módulos APIRouter

from adapters.inbound.routes.query import router as query_router
from adapters.inbound.routes.health import router as health_router
from adapters.inbound.routes.session import router as session_router
from adapters.inbound.routes.admin import router as admin_router

__all__ = ["query_router", "health_router", "session_router", "admin_router"]
