from __future__ import annotations

from typing import Iterable

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


class AprioriService:
    def __init__(self) -> None:
        self.rules = pd.DataFrame()
        self.relative_support: float = 0.0

    def fit(self, interactions_df: pd.DataFrame, absolute_support: int = 3, max_len: int = 3) -> None:
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

    def get_candidates(self, basket_ids: Iterable[str]) -> list[str]:
        if self.rules.empty:
            return []

        basket_set = frozenset(str(item) for item in basket_ids)
        candidate_scores: dict[str, tuple[float, float]] = {}

        for _, row in self.rules.iterrows():
            antecedents = frozenset(str(item) for item in row.get("antecedents", []))
            consequents = [str(item) for item in row.get("consequents", [])]
            if not antecedents.issubset(basket_set):
                continue

            lift = float(row.get("lift", 0.0))
            confidence = float(row.get("confidence", 0.0))
            score = (lift, confidence)

            for item in consequents:
                if item in basket_set:
                    continue
                current_score = candidate_scores.get(item)
                if current_score is None or score > current_score:
                    candidate_scores[item] = score

        ordered = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)
        return [item_id for item_id, _ in ordered]
