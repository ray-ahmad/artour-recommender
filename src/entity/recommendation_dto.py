from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    data: T


class AprioriExplanation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lift: float
    confidence: float
    support: float
    antecedents: list[str] = Field(default_factory=list)


class CbfExplanation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    similarity_score: float = Field(validation_alias=AliasChoices("similarity_score", "similarityScore"), serialization_alias="similarityScore")


class McrsExplanation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    price: float
    rating: float
    min_price: float = Field(validation_alias=AliasChoices("min_price", "minPrice"), serialization_alias="minPrice")
    max_price: float = Field(validation_alias=AliasChoices("max_price", "maxPrice"), serialization_alias="maxPrice")
    cost_score: float = Field(validation_alias=AliasChoices("cost_score", "costScore"), serialization_alias="costScore")
    benefit_score: float = Field(validation_alias=AliasChoices("benefit_score", "benefitScore"), serialization_alias="benefitScore")
    weight_cost: float = Field(validation_alias=AliasChoices("weight_cost", "weightCost"), serialization_alias="weightCost")
    weight_benefit: float = Field(validation_alias=AliasChoices("weight_benefit", "weightBenefit"), serialization_alias="weightBenefit")
    final_score: float = Field(validation_alias=AliasChoices("final_score", "finalScore"), serialization_alias="finalScore")


class RecommendationExplanation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    apriori: AprioriExplanation | None = None
    cbf: CbfExplanation | None = None
    mcrs: McrsExplanation


class RecommendationItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_id: str = Field(validation_alias=AliasChoices("place_id", "placeId"), serialization_alias="placeId")
    score: float
    rank: int
    source: str
    explanation: RecommendationExplanation


class UserToItemRecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["user-to-item"] = "user-to-item"
    basket_ids: list[str] = Field(default_factory=list, validation_alias=AliasChoices("basket_ids", "basketIds"), serialization_alias="basketIds")
    k: int
    generated_at: datetime = Field(validation_alias=AliasChoices("generated_at", "generatedAt"), serialization_alias="generatedAt")
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class ItemToItemRecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["item-to-item"] = "item-to-item"
    anchor_id: str = Field(validation_alias=AliasChoices("anchor_id", "anchorId"), serialization_alias="anchorId")
    k: int
    generated_at: datetime = Field(validation_alias=AliasChoices("generated_at", "generatedAt"), serialization_alias="generatedAt")
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)


class UserToItemRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    basket_ids: list[str] = Field(default_factory=list, validation_alias=AliasChoices("basket_ids", "basketIds"), serialization_alias="basketIds")
    k: int | None = Field(default=None, gt=0)


UserToItemEnvelope = BaseResponse[UserToItemRecommendationResponse]
ItemToItemEnvelope = BaseResponse[ItemToItemRecommendationResponse]
