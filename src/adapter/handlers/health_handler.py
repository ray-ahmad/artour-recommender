from __future__ import annotations

from typing import cast
from fastapi import APIRouter, Depends

from src.adapter.handlers.dependencies import get_recommendation_service
from src.adapter.presenter.admin import HealthOutput
from src.module.recommendation.service import RecommendationService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOutput)
def health(service: RecommendationService = Depends(get_recommendation_service)) -> HealthOutput:
    snapshot = service.health_snapshot()
    places_count = int(cast(int, snapshot.get("places_count", 0)))
    interactions_count = int(cast(int, snapshot.get("interactions_count", 0)))
    return HealthOutput(
        status="ok",
        ready=bool(snapshot.get("ready", False)),
        places_count=places_count,
        interactions_count=interactions_count,
    )
