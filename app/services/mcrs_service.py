from __future__ import annotations

from typing import Mapping, cast


class MCRSService:
    def __init__(self, min_rating_scale: float, max_rating_scale: float, weight_cost: float, weight_benefit: float) -> None:
        self.min_rating_scale = min_rating_scale
        self.max_rating_scale = max_rating_scale
        self.weight_cost = weight_cost
        self.weight_benefit = weight_benefit

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

            if self.max_rating_scale > self.min_rating_scale:
                normalized_rating = (rating - self.min_rating_scale) / (self.max_rating_scale - self.min_rating_scale)
            else:
                normalized_rating = 0.0
            benefit_score = max(0.0, min(1.0, normalized_rating))

            final_score = (self.weight_cost * cost_score) + (self.weight_benefit * benefit_score)
            scored_candidates.append({"place_id": str(place_id), "score": float(final_score)})

        scored_candidates.sort(key=lambda item: float(cast(float, item.get("score", 0.0))), reverse=True)
        return scored_candidates[:limit]
