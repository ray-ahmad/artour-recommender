from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_recommendation_service
from app.api.schemas.recommendation import RefreshEnvelope, RefreshResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["admin"])


@router.post("/refresh", response_model=RefreshEnvelope)
async def refresh(service: RecommendationService = Depends(get_recommendation_service)) -> RefreshEnvelope:
    try:
        await service.refresh()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RefreshEnvelope(
        data=RefreshResponse(
            status="refreshed",
            places_count=service.places_count,
            interactions_count=service.interactions_count,
            refreshed_at=datetime.now(timezone.utc),
        )
    )
