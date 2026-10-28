from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar, cast

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseOutput(BaseModel, Generic[T]):
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

    similarity_score: float = Field(
        validation_alias=AliasChoices("similarity_score", "similarityScore"),
        serialization_alias="similarityScore",
    )


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


class RecommendationItemOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_id: str = Field(validation_alias=AliasChoices("place_id", "placeId"), serialization_alias="placeId")
    score: float
    rank: int
    source: str
    explanation: RecommendationExplanation


class UserToItemOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["user-to-item"] = "user-to-item"
    basket_ids: list[str] = Field(default_factory=list, validation_alias=AliasChoices("basket_ids", "basketIds"), serialization_alias="basketIds")
    k: int
    generated_at: datetime = Field(validation_alias=AliasChoices("generated_at", "generatedAt"), serialization_alias="generatedAt")
    recommendations: list[RecommendationItemOutput] = Field(default_factory=list)


class ItemToItemOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["item-to-item"] = "item-to-item"
    anchor_id: str = Field(validation_alias=AliasChoices("anchor_id", "anchorId"), serialization_alias="anchorId")
    k: int
    generated_at: datetime = Field(validation_alias=AliasChoices("generated_at", "generatedAt"), serialization_alias="generatedAt")
    recommendations: list[RecommendationItemOutput] = Field(default_factory=list)


class UserToItemInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    basket_ids: list[str] = Field(default_factory=list, validation_alias=AliasChoices("basket_ids", "basketIds"), serialization_alias="basketIds")
    k: int | None = Field(default=None, gt=0)


UserToItemEnvelopeOutput = BaseOutput[UserToItemOutput]
ItemToItemEnvelopeOutput = BaseOutput[ItemToItemOutput]


# --- Pure Conversion Functions (new_<target>_from_<source>) ---

def new_apriori_explanation_from_dict(raw: dict[str, object]) -> AprioriExplanation:
    raw_antecedents = raw.get("antecedents")
    antecedents = [str(x) for x in raw_antecedents] if isinstance(raw_antecedents, list) else []
    lift_val = raw.get("lift", 0.0)
    conf_val = raw.get("confidence", 0.0)
    sup_val = raw.get("support", 0.0)
    return AprioriExplanation(
        lift=float(str(lift_val)) if lift_val is not None else 0.0,
        confidence=float(str(conf_val)) if conf_val is not None else 0.0,
        support=float(str(sup_val)) if sup_val is not None else 0.0,
        antecedents=antecedents,
    )


def new_cbf_explanation_from_dict(raw: dict[str, object]) -> CbfExplanation:
    score_val = raw.get("score", 0.0)
    return CbfExplanation(
        similarity_score=float(str(score_val)) if score_val is not None else 0.0,
    )


def new_mcrs_explanation_from_dict(raw: dict[str, object]) -> McrsExplanation:
    def _to_float(key: str) -> float:
        val = raw.get(key, 0.0)
        return float(str(val)) if val is not None else 0.0

    return McrsExplanation(
        price=_to_float("price"),
        rating=_to_float("rating"),
        min_price=_to_float("min_price"),
        max_price=_to_float("max_price"),
        cost_score=_to_float("cost_score"),
        benefit_score=_to_float("benefit_score"),
        weight_cost=_to_float("weight_cost"),
        weight_benefit=_to_float("weight_benefit"),
        final_score=_to_float("final_score"),
    )


def new_recommendation_explanation_from_dict(raw: dict[str, object]) -> RecommendationExplanation:
    apriori_raw = raw.get("apriori")
    cbf_raw = raw.get("cbf")
    mcrs_raw = cast(dict[str, object], raw.get("mcrs") or {})

    return RecommendationExplanation(
        apriori=new_apriori_explanation_from_dict(cast(dict[str, object], apriori_raw)) if apriori_raw else None,
        cbf=new_cbf_explanation_from_dict(cast(dict[str, object], cbf_raw)) if cbf_raw else None,
        mcrs=new_mcrs_explanation_from_dict(mcrs_raw),
    )


def new_recommendation_item_output_from_dict(item: dict[str, object]) -> RecommendationItemOutput:
    score_val = item.get("score", 0.0)
    rank_val = item.get("rank", 0)
    raw_explanation = cast(dict[str, object], item.get("explanation") or {})

    return RecommendationItemOutput(
        place_id=str(item.get("place_id", "")),
        score=float(str(score_val)) if score_val is not None else 0.0,
        rank=int(str(rank_val)) if rank_val is not None else 0,
        source=str(item.get("source", "unknown")),
        explanation=new_recommendation_explanation_from_dict(raw_explanation),
    )
