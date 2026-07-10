from __future__ import annotations

import logging
from typing import Mapping, cast

logger = logging.getLogger(__name__)


class MCRSService:
    def __init__(
        self,
        min_rating_scale: float,
        max_rating_scale: float,
        weight_cost: float,
        weight_benefit: float,
        neutral_rating_score: float = 0.5,
    ) -> None:
        self.min_rating_scale = min_rating_scale
        self.max_rating_scale = max_rating_scale
        self.weight_cost = weight_cost
        self.weight_benefit = weight_benefit
        self.neutral_rating_score = neutral_rating_score

    def rank(
        self,
        candidate_ids: list[str],
        place_lookup: Mapping[str, dict[str, float]],
        min_price: float,
        max_price: float,
        limit: int,
    ) -> list[dict[str, object]]:
        if not candidate_ids or limit <= 0:
            return []

        scored_candidates: list[dict[str, object]] = []
        for place_id in candidate_ids:
            stats = place_lookup.get(str(place_id))
            if not stats:
                continue

            price = float(stats.get("placePrice", 0.0) or 0.0)
            rating = float(stats.get("placeRating", 0.0) or 0.0)

            if max_price > min_price:
                normalized_price = (price - min_price) / (max_price - min_price)
            else:
                normalized_price = 0.0
            cost_score = 1.0 - max(0.0, min(1.0, normalized_price))

            if rating <= 0.0:
                benefit_score = self.neutral_rating_score
            elif self.max_rating_scale > self.min_rating_scale:
                normalized_rating = (rating - self.min_rating_scale) / (self.max_rating_scale - self.min_rating_scale)
                benefit_score = max(0.0, min(1.0, normalized_rating))
            else:
                benefit_score = 0.0

            final_score = (self.weight_cost * cost_score) + (self.weight_benefit * benefit_score)
            scored_candidates.append(
                {
                    "place_id": str(place_id),
                    "score": float(final_score),
                    "price": price,
                    "rating": rating,
                    "min_price": float(min_price),
                    "max_price": float(max_price),
                    "cost_score": float(cost_score),
                    "benefit_score": float(benefit_score),
                    "weight_cost": float(self.weight_cost),
                    "weight_benefit": float(self.weight_benefit),
                }
            )

        logger.info(
            "MCRS scoring (pre-sort): candidates=%s limit=%s minPrice=%.2f maxPrice=%.2f weightCost=%.2f weightBenefit=%.2f",
            len(scored_candidates),
            limit,
            min_price,
            max_price,
            self.weight_cost,
            self.weight_benefit,
        )
        for entry in scored_candidates:
            logger.debug(
                "MCRS candidate: placeId=%s price=%.2f rating=%.2f costScore=%.4f benefitScore=%.4f finalScore=%.4f",
                entry["place_id"],
                entry["price"],
                entry["rating"],
                entry["cost_score"],
                entry["benefit_score"],
                entry["score"],
            )

        scored_candidates.sort(key=lambda item: float(cast(float, item.get("score", 0.0))), reverse=True)
        return scored_candidates[:limit]