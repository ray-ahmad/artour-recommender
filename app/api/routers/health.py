from typing import cast

from fastapi import APIRouter, Depends

from app.api.dependencies import get_recommendation_service
from app.api.schemas import HealthResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(service: RecommendationService = Depends(get_recommendation_service)) -> HealthResponse:
    snapshot = service.health_snapshot()
    places_count = int(cast(int, snapshot.get("places_count", 0)))
    interactions_count = int(cast(int, snapshot.get("interactions_count", 0)))
    return HealthResponse(
        status="ok",
        ready=bool(snapshot.get("ready", False)),
        places_count=places_count,
        interactions_count=interactions_count,
    )
