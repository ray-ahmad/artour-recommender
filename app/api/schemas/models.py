from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserToItemRequest(BaseModel):
    basket_ids: list[str] = Field(min_length=1)
    k: int | None = Field(default=None, gt=0)


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


class HealthResponse(BaseModel):
    status: str
    ready: bool
    places_count: int
    interactions_count: int
