from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.adapter.handlers.dependencies import get_recommendation_service
from src.adapter.presenter.recommendation import (
    ItemToItemEnvelopeOutput,
    ItemToItemOutput,
    UserToItemEnvelopeOutput,
    UserToItemInput,
    UserToItemOutput,
    new_recommendation_item_output_from_dict,
)
from src.module.recommendation.service import RecommendationService

router = APIRouter(tags=["recommendations"])


@router.post("/recommend/user-to-item", response_model=UserToItemEnvelopeOutput)
def recommend_user_to_item(
    payload: UserToItemInput,
    service: RecommendationService = Depends(get_recommendation_service),
) -> UserToItemEnvelopeOutput:
    try:
        recommendations = service.recommend_user_to_item(payload.basket_ids, payload.k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return UserToItemEnvelopeOutput(
        data=UserToItemOutput(
            basket_ids=[str(item) for item in payload.basket_ids],
            k=int(payload.k or service.settings.default_recommendation_k),
            generated_at=datetime.now(timezone.utc),
            recommendations=[new_recommendation_item_output_from_dict(item) for item in recommendations],
        )
    )


@router.get("/recommend/item-to-item/{item_id}", response_model=ItemToItemEnvelopeOutput)
def recommend_item_to_item(
    item_id: str,
    k: int | None = Query(default=None, gt=0),
    service: RecommendationService = Depends(get_recommendation_service),
) -> ItemToItemEnvelopeOutput:
    try:
        recommendations = service.recommend_item_to_item(item_id, k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ItemToItemEnvelopeOutput(
        data=ItemToItemOutput(
            anchor_id=str(item_id),
            k=int(k or service.settings.default_recommendation_k),
            generated_at=datetime.now(timezone.utc),
            recommendations=[new_recommendation_item_output_from_dict(item) for item in recommendations],
        )
    )
