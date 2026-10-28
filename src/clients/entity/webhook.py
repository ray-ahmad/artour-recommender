from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RefreshWebhookRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_id: str = Field(validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")
    status: Literal["success", "failed"]
    finished_at: datetime = Field(validation_alias=AliasChoices("finished_at", "finishedAt"), serialization_alias="finishedAt")
    places_count: int | None = Field(default=None, validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
    interactions_count: int | None = Field(default=None, validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")
    error: str | None = None
