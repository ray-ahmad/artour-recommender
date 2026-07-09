from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

logger = logging.getLogger(__name__)


class AprioriService:
    def __init__(self) -> None:
        self.rules = pd.DataFrame()
        self.relative_support: float = 0.0

    def fit(
        self,
        interactions_df: pd.DataFrame,
        absolute_support: int = 3,
        max_len: int = 3,
        min_user_interactions: int = 2,
    ) -> None:
        self.rules = pd.DataFrame()
        self.relative_support = 0.0

        if interactions_df.empty:
            return

        required_columns = {"userId", "refId"}
        if not required_columns.issubset(interactions_df.columns):
            return

        valid_df = interactions_df.copy()
        valid_df = valid_df[valid_df["userId"].notna() & valid_df["refId"].notna()]
        if valid_df.empty:
            return

        # Remove users with too few interactions so Apriori learns meaningful co-occurrence patterns.
        interaction_counts = valid_df.groupby(valid_df["userId"].astype(str))["refId"].size()
        eligible_users = interaction_counts[interaction_counts >= max(1, int(min_user_interactions))].index
        if len(eligible_users) == 0:
            return

        valid_df = valid_df[valid_df["userId"].astype(str).isin(eligible_users)]
        if valid_df.empty:
            return

        basket = pd.crosstab(valid_df["userId"].astype(str), valid_df["refId"].astype(str))
        basket = basket > 0
        total_transactions = basket.shape[0]
        if total_transactions == 0:
            return

        self.relative_support = absolute_support / total_transactions
        if self.relative_support >= 1.0:
            return

        frequent_itemsets = apriori(basket, min_support=self.relative_support, use_colnames=True, max_len=max_len)
        if frequent_itemsets.empty:
            return

        try:
            self.rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
        except ValueError:
            self.rules = pd.DataFrame()

    def get_candidates_with_explanations(self, basket_ids: Iterable[str]) -> list[dict[str, object]]:
        """Ordered candidates with the winning rule's metrics, same order/tie-break as get_candidates().

        Each item: {"place_id": str, "lift": float, "confidence": float, "support": float, "antecedents": list[str]}
        """
        if self.rules.empty:
            return []

        basket_set = frozenset(str(item) for item in basket_ids)
        candidate_best: dict[str, dict[str, object]] = {}

        for _, row in self.rules.iterrows():
            antecedents = frozenset(str(item) for item in row.get("antecedents", []))
            consequents = [str(item) for item in row.get("consequents", [])]
            if not antecedents.issubset(basket_set):
                continue

            lift = float(row.get("lift", 0.0))
            confidence = float(row.get("confidence", 0.0))
            support = float(row.get("support", 0.0))

            for item in consequents:
                if item in basket_set:
                    continue
                current = candidate_best.get(item)
                current_score = (current["lift"], current["confidence"]) if current is not None else None
                if current_score is None or (lift, confidence) > current_score:
                    candidate_best[item] = {
                        "place_id": item,
                        "lift": lift,
                        "confidence": confidence,
                        "support": support,
                        "antecedents": sorted(antecedents),
                    }

        ordered = sorted(
            candidate_best.values(),
            key=lambda entry: (entry["lift"], entry["confidence"]),
            reverse=True,
        )
        logger.info(
            "Apriori candidate scoring: basketSize=%s rules=%s matchedCandidates=%s top5=%s",
            len(basket_set),
            int(self.rules.shape[0]),
            len(ordered),
            [(entry["place_id"], round(entry["lift"], 3), round(entry["confidence"], 3)) for entry in ordered[:5]],
        )
        return ordered

    def get_candidates(self, basket_ids: Iterable[str]) -> list[str]:
        return [str(entry["place_id"]) for entry in self.get_candidates_with_explanations(basket_ids)]
