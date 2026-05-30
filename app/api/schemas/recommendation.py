from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    data: T


class RecommendationItemResponse(BaseModel):
    place_id: str
    score: float
    rank: int
    source: str


class UserToItemRecommendationResponse(BaseModel):
    mode: Literal["user-to-item"] = "user-to-item"
    basket_ids: list[str] = Field(default_factory=list)
    k: int
    generated_at: datetime
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class ItemToItemRecommendationResponse(BaseModel):
    mode: Literal["item-to-item"] = "item-to-item"
    anchor_id: str
    k: int
    generated_at: datetime
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class RefreshResponse(BaseModel):
    status: str
    places_count: int
    interactions_count: int
    refreshed_at: datetime


UserToItemEnvelope = BaseResponse[UserToItemRecommendationResponse]
ItemToItemEnvelope = BaseResponse[ItemToItemRecommendationResponse]
RefreshEnvelope = BaseResponse[RefreshResponse]
