from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_recommendation_service
from app.api.schemas.recommendation import (
    AprioriExplanation,
    CbfExplanation,
    ItemToItemEnvelope,
    ItemToItemRecommendationResponse,
    McrsExplanation,
    RecommendationExplanation,
    RecommendationItemResponse,
    UserToItemEnvelope,
    UserToItemRecommendationResponse,
)
from app.api.schemas.models import UserToItemRequest
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["recommendations"])


def _float(source: dict[str, object], key: str) -> float:
    return float(cast(float, source.get(key, 0.0)))


def _build_explanation(raw: dict[str, object]) -> RecommendationExplanation:
    apriori_raw = raw.get("apriori")
    cbf_raw = raw.get("cbf")
    mcrs_raw = cast(dict[str, object], raw.get("mcrs") or {})

    return RecommendationExplanation(
        apriori=AprioriExplanation(**cast(dict[str, object], apriori_raw)) if apriori_raw else None,
        cbf=CbfExplanation(similarity_score=_float(cast(dict[str, object], cbf_raw), "score")) if cbf_raw else None,
        mcrs=McrsExplanation(
            price=_float(mcrs_raw, "price"),
            rating=_float(mcrs_raw, "rating"),
            min_price=_float(mcrs_raw, "min_price"),
            max_price=_float(mcrs_raw, "max_price"),
            cost_score=_float(mcrs_raw, "cost_score"),
            benefit_score=_float(mcrs_raw, "benefit_score"),
            weight_cost=_float(mcrs_raw, "weight_cost"),
            weight_benefit=_float(mcrs_raw, "weight_benefit"),
            final_score=_float(mcrs_raw, "final_score"),
        ),
    )


def _build_response_items(items: list[dict[str, object]]) -> list[RecommendationItemResponse]:
    return [
        RecommendationItemResponse(
            place_id=str(item.get("place_id", "")),
            score=float(item.get("score", 0.0)),
            rank=int(item.get("rank", 0)),
            source=str(item.get("source", "unknown")),
            explanation=_build_explanation(cast(dict[str, object], item.get("explanation") or {})),
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
