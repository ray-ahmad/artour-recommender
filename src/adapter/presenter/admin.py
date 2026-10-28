from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.adapter.presenter.recommendation import BaseOutput


class RefreshOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    places_count: int = Field(validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int = Field(validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")
    refreshed_at: datetime = Field(validation_alias=AliasChoices("refreshed_at", "refreshedAt"), serialization_alias="refreshedAt")


class RefreshTriggerInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str | None = Field(default=None, validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")


class RefreshAcceptedOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["accepted"] = "accepted"
    refresh_id: str = Field(validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")
    accepted_at: datetime = Field(validation_alias=AliasChoices("accepted_at", "acceptedAt"), serialization_alias="acceptedAt")


class HealthOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    ready: bool
    places_count: int = Field(validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int = Field(validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")


RefreshEnvelopeOutput = BaseOutput[RefreshOutput]
RefreshAcceptedEnvelopeOutput = BaseOutput[RefreshAcceptedOutput]
