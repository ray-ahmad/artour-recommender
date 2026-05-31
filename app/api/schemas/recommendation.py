from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    data: T


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


class RefreshTriggerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str | None = Field(default=None, alias="refreshId")


class RefreshAcceptedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["accepted"] = "accepted"
    refresh_id: str = Field(alias="refreshId")
    accepted_at: datetime = Field(alias="acceptedAt")


class RefreshWebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str = Field(alias="refreshId")
    status: Literal["success", "failed"]
    finished_at: datetime = Field(alias="finishedAt")
    places_count: int | None = Field(default=None, alias="placesCount")
    interactions_count: int | None = Field(default=None, alias="interactionsCount")
    error: str | None = None


UserToItemEnvelope = BaseResponse[UserToItemRecommendationResponse]
ItemToItemEnvelope = BaseResponse[ItemToItemRecommendationResponse]
RefreshEnvelope = BaseResponse[RefreshResponse]
RefreshAcceptedEnvelope = BaseResponse[RefreshAcceptedResponse]
