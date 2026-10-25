from src.adapter.handlers.health_handler import router as health_router
from src.adapter.handlers.admin_handler import router as admin_router
from src.adapter.handlers.recommendation_handler import router as recommendation_router
from src.adapter.handlers.dependencies import get_recommendation_service, get_refresh_webhook_client

__all__ = [
    "health_router",
    "admin_router",
    "recommendation_router",
    "get_recommendation_service",
    "get_refresh_webhook_client",
]
