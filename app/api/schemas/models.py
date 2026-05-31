from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserToItemRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    basket_ids: list[str] = Field(default_factory=list, alias="basketIds")
    k: int | None = Field(default=None, gt=0)


class RecommendationItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_id: str = Field(alias="placeId")
    score: float
    rank: int
    source: str


class UserToItemRecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["user-to-item"] = "user-to-item"
    basket_ids: list[str] = Field(default_factory=list, alias="basketIds")
    k: int
    generated_at: datetime = Field(alias="generatedAt")
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class ItemToItemRecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["item-to-item"] = "item-to-item"
    anchor_id: str = Field(alias="anchorId")
    k: int
    generated_at: datetime = Field(alias="generatedAt")
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class RefreshResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    places_count: int = Field(alias="placesCount")
    interactions_count: int = Field(alias="interactionsCount")
    refreshed_at: datetime = Field(alias="refreshedAt")


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    ready: bool
    places_count: int = Field(alias="placesCount")
    interactions_count: int = Field(alias="interactionsCount")
