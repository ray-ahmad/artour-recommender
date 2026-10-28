from __future__ import annotations

import logging
from typing import Iterable, cast

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

from src.entity.recommendation import AprioriFitParams

logger = logging.getLogger(__name__)


class AprioriService:
    def __init__(self) -> None:
        self.rules = pd.DataFrame()
        self.relative_support: float = 0.0

    def fit(
        self,
        interactions_df: pd.DataFrame,
        params: AprioriFitParams | None = None,
    ) -> None:
        cfg = params or AprioriFitParams()
        self.rules = pd.DataFrame()
        self.relative_support = 0.0

        if interactions_df.empty:
            return

        required_columns = {"userId", "refId"}
        if not required_columns.issubset(interactions_df.columns):
            return

        valid_df = interactions_df.copy()
        user_not_na = cast(pd.Series, valid_df["userId"].notna())
        ref_not_na = cast(pd.Series, valid_df["refId"].notna())
        valid_df = cast(pd.DataFrame, valid_df[user_not_na & ref_not_na])
        if valid_df.empty:
            return

        user_col = cast(pd.Series, valid_df["userId"].astype(str))
        interaction_counts = cast(pd.Series, valid_df.groupby(user_col)["refId"].size())
        filtered_counts = cast(pd.Series, interaction_counts[interaction_counts >= max(1, int(cfg.min_user_interactions))])
        eligible_users = set(filtered_counts.index.tolist())
        if not eligible_users:
            return

        valid_df = cast(pd.DataFrame, valid_df[user_col.isin(eligible_users)])
        if valid_df.empty:
            return

        basket = pd.crosstab(valid_df["userId"].astype(str), valid_df["refId"].astype(str))
        basket = basket > 0
        total_transactions = basket.shape[0]
        if total_transactions == 0:
            return

        self.relative_support = cfg.absolute_support / total_transactions
        if self.relative_support >= 1.0:
            return

        frequent_itemsets = apriori(basket, min_support=self.relative_support, use_colnames=True, max_len=cfg.max_len)
        if frequent_itemsets.empty:
            return

        try:
            self.rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
        except ValueError:
            self.rules = pd.DataFrame()

    def get_candidates_with_explanations(self, basket_ids: Iterable[str]) -> list[dict[str, object]]:
        if self.rules.empty:
            return []

        basket_set = frozenset(str(item) for item in basket_ids)
        candidate_best: dict[str, dict[str, object]] = {}

        for _, row in self.rules.iterrows():
            raw_antecedents = row.get("antecedents")
            antecedents = frozenset(str(item) for item in cast(Iterable[object], raw_antecedents)) if raw_antecedents is not None else frozenset()
            raw_consequents = row.get("consequents")
            consequents = [str(item) for item in cast(Iterable[object], raw_consequents)] if raw_consequents is not None else []
            if not antecedents.issubset(basket_set):
                continue

            lift = float(cast(float, row.get("lift", 0.0)))
            confidence = float(cast(float, row.get("confidence", 0.0)))
            support = float(cast(float, row.get("support", 0.0)))

            for item in consequents:
                if item in basket_set:
                    continue
                current = candidate_best.get(item)
                current_lift = cast(float, current["lift"]) if current is not None else None
                if current_lift is None or lift > current_lift:
                    candidate_best[item] = {
                        "place_id": item,
                        "lift": lift,
                        "confidence": confidence,
                        "support": support,
                        "antecedents": sorted(antecedents),
                    }

        ordered = sorted(
            candidate_best.values(),
            key=lambda entry: cast(float, entry["lift"]),
            reverse=True,
        )
        logger.info(
            "Apriori candidate scoring: basketSize=%s rules=%s matchedCandidates=%s top5=%s",
            len(basket_set),
            int(self.rules.shape[0]),
            len(ordered),
            [
                (entry["place_id"], round(cast(float, entry["lift"]), 3), round(cast(float, entry["confidence"]), 3))
                for entry in ordered[:5]
            ],
        )
        return ordered

    def get_candidates(self, basket_ids: Iterable[str]) -> list[str]:
        return [str(entry["place_id"]) for entry in self.get_candidates_with_explanations(basket_ids)]
