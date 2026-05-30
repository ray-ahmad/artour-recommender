from .admin import router as admin_router
from .health import router as health_router
from .recommendations import router as recommendations_router

__all__ = ["admin_router", "health_router", "recommendations_router"]
