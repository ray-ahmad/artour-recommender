from fastapi import Request

from app.services.recommendation_service import RecommendationService


def get_recommendation_service(request: Request) -> RecommendationService:
    service = getattr(request.app.state, "recommendation_service", None)
    if service is None:
        raise RuntimeError("Recommendation service is not initialized.")
    return service
