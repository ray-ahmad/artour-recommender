from fastapi import APIRouter, Depends

from app.api.dependencies import get_recommendation_service
from app.api.schemas import HealthResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(service: RecommendationService = Depends(get_recommendation_service)) -> HealthResponse:
    snapshot = service.health_snapshot()
    return HealthResponse(
        status="ok",
        ready=bool(snapshot["ready"]),
        places_count=int(snapshot["places_count"]),
        interactions_count=int(snapshot["interactions_count"]),
    )
