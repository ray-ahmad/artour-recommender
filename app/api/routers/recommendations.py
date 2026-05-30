from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_recommendation_service
from app.api.schemas.recommendation import (
    ItemToItemEnvelope,
    ItemToItemRecommendationResponse,
    RecommendationItemResponse,
    UserToItemEnvelope,
    UserToItemRecommendationResponse,
    UserToItemRequest,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["recommendations"])


def _build_response_items(items: list[dict[str, object]]) -> list[RecommendationItemResponse]:
    return [
        RecommendationItemResponse(
            place_id=str(item["place_id"]),
            score=float(item["score"]),
            rank=int(item["rank"]),
            source=str(item["source"]),
        )
        for item in items
    ]


@router.post("/recommend/user-to-item", response_model=UserToItemEnvelope)
def recommend_user_to_item(
    payload: UserToItemRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> UserToItemEnvelope:
    try:
        recommendations = service.recommend_user_to_item(payload.basket_ids, payload.k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return UserToItemEnvelope(
        data=UserToItemRecommendationResponse(
            basket_ids=[str(item) for item in payload.basket_ids],
            k=int(payload.k or service.settings.default_recommendation_k),
            generated_at=datetime.now(timezone.utc),
            recommendations=_build_response_items(recommendations),
        )
    )


@router.get("/recommend/item-to-item/{item_id}", response_model=ItemToItemEnvelope)
def recommend_item_to_item(
    item_id: str,
    k: int | None = Query(default=None, gt=0),
    service: RecommendationService = Depends(get_recommendation_service),
) -> ItemToItemEnvelope:
    try:
        recommendations = service.recommend_item_to_item(item_id, k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ItemToItemEnvelope(
        data=ItemToItemRecommendationResponse(
            anchor_id=str(item_id),
            k=int(k or service.settings.default_recommendation_k),
            generated_at=datetime.now(timezone.utc),
            recommendations=_build_response_items(recommendations),
        )
    )
