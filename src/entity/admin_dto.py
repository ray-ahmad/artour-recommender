from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.entity.recommendation_dto import BaseResponse


class RefreshResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    places_count: int = Field(validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int = Field(validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")
    refreshed_at: datetime = Field(validation_alias=AliasChoices("refreshed_at", "refreshedAt"), serialization_alias="refreshedAt")


class RefreshTriggerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str | None = Field(default=None, validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")


class RefreshAcceptedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["accepted"] = "accepted"
    refresh_id: str = Field(validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")
    accepted_at: datetime = Field(validation_alias=AliasChoices("accepted_at", "acceptedAt"), serialization_alias="acceptedAt")


class RefreshWebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str = Field(validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")
    status: Literal["success", "failed"]
    finished_at: datetime = Field(validation_alias=AliasChoices("finished_at", "finishedAt"), serialization_alias="finishedAt")
    places_count: int | None = Field(default=None, validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int | None = Field(default=None, validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")
    error: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    ready: bool
    places_count: int = Field(validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int = Field(validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")


RefreshEnvelope = BaseResponse[RefreshResponse]
RefreshAcceptedEnvelope = BaseResponse[RefreshAcceptedResponse]
