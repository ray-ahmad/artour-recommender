from __future__ import annotations

from fastapi import APIRouter

from src.adapter.handlers.admin_handler import router as admin_router
from src.adapter.handlers.health_handler import router as health_router
from src.adapter.handlers.recommendation_handler import router as recommendation_router


def init_routes() -> APIRouter:
    root_router = APIRouter()
    root_router.include_router(health_router)
    root_router.include_router(admin_router)
    root_router.include_router(recommendation_router)
    return root_router
