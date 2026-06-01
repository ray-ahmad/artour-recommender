from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.configs.settings import Settings, get_settings
from app.repositories.artour_repository import ArtourRepository, DataBundle
from app.services.apriori_service import AprioriService
from app.services.cbf_service import CBFService
from app.services.mcrs_service import MCRSService
from app.services.text_preprocessor import TextPreprocessor
from typing import cast


class RecommendationService:
    def __init__(self, repository: ArtourRepository, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("uvicorn.error")
        _default_cache = (
            "/tmp/recommendation_state.pkl"
            if os.getenv("SPACE_ID")
            else str(Path(__file__).resolve().parents[2] / ".cache" / "recommendation_state.pkl")
        )
        self.state_filepath = os.getenv("ARTOUR_RECOMMENDATION_STATE_PATH", _default_cache)
        self.text_preprocessor = TextPreprocessor()
        self.cbf_service = CBFService()
        self.apriori_service = AprioriService()
        self.mcrs_service = MCRSService(
            min_rating_scale=self.settings.mcrs_min_rating_scale,
            max_rating_scale=self.settings.mcrs_max_rating_scale,
            weight_cost=self.settings.weight_cost,
            weight_benefit=self.settings.weight_benefit,
        )
        self._ready = False
        self._places_df = pd.DataFrame()
        self._interactions_df = pd.DataFrame()
        self._place_lookup: dict[str, dict[str, float]] = {}
        self._min_price = 0.0
        self._max_price = 0.0

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def places_count(self) -> int:
        return int(self._places_df.shape[0])

    @property
    def interactions_count(self) -> int:
        return int(self._interactions_df.shape[0])

    def _clean_interactions(self, interactions_df: pd.DataFrame, known_place_ids: set[str]) -> pd.DataFrame:
        if interactions_df.empty:
            return pd.DataFrame(columns=["userId", "refId", "refModule", "type", "value", "createdAt"])

        df = interactions_df.copy()
        required_columns = {"userId", "refId", "refModule", "type"}
        if not required_columns.issubset(df.columns):
            return pd.DataFrame(columns=["userId", "refId", "refModule", "type", "value", "createdAt"])

        for column in ("userId", "refId", "refModule", "type"):
            if column in df.columns:
                df[column] = df[column].fillna("").astype(str)

        if "createdAt" in df.columns:
            df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")
        else:
            df["createdAt"] = pd.NaT

        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
        else:
            df["value"] = 0.0

        if "refModule" in df.columns:
            df = df[df["refModule"].str.upper() == "PLACE"]

        if "refId" in df.columns:
            df = df[df["refId"].isin(known_place_ids)]

        def get_toggle_group(action_type: str) -> str:
            if action_type in {"PLACE_LIKE", "PLACE_UNLIKE"}:
                return "TOGGLE_LIKE"
            if action_type in {"PLACE_BOOKMARK", "PLACE_UNBOOKMARK"}:
                return "TOGGLE_BOOKMARK"
            if action_type in {"PLACE_DISLIKE", "PLACE_UNDISLIKE"}:
                return "TOGGLE_DISLIKE"
            return action_type

        if "type" in df.columns:
            df["interaction_group"] = df["type"].map(get_toggle_group)
        else:
            df["interaction_group"] = "UNKNOWN"

        if {"userId", "refId", "interaction_group"}.issubset(df.columns):
            df = df.sort_values(by="createdAt")
            df = df.groupby(["userId", "refId", "interaction_group"], dropna=False).tail(1).copy()

        positive_review_mask = df["type"].eq("PLACE_REVIEW") & (df["value"] >= self.settings.min_positive_rating)
        positive_action_mask = df["type"].isin({"PLACE_LIKE", "PLACE_BOOKMARK", "PLACE_SHARE"})
        df = df[positive_review_mask | positive_action_mask].copy()
        return df.reset_index(drop=True)

    @staticmethod
    def _build_place_lookup(places_df: pd.DataFrame) -> dict[str, dict[str, float]]:
        lookup: dict[str, dict[str, float]] = {}
        if places_df.empty:
            return lookup

        for _, row in places_df.iterrows():
            place_id = str(row.get("placeId", ""))
            if not place_id:
                continue
            price_value = pd.to_numeric(row.get("placePrice", 0), errors="coerce")
            rating_value = pd.to_numeric(row.get("placeRating", 0), errors="coerce")
            lookup[place_id] = {
                "placePrice": float(0.0 if pd.isna(price_value) else price_value),
                "placeRating": float(0.0 if pd.isna(rating_value) else rating_value),
            }
        return lookup

    @staticmethod
    def _merge_source(existing: str | None, new_source: str) -> str:
        if not existing:
            return new_source
        if existing == new_source:
            return existing
        existing_parts = existing.split("+")
        if new_source not in existing_parts:
            existing_parts.append(new_source)
        return "+".join(existing_parts)

    def save_state(self, filepath: str) -> None:
        self.logger.info("Saving recommendation state: path=%s", filepath)
        state_path = Path(filepath)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "places_df": self._places_df,
            "interactions_df": self._interactions_df,
            "place_lookup": self._place_lookup,
            "min_price": self._min_price,
            "max_price": self._max_price,
            "cbf_state": {
                "vectorizer": self.cbf_service.vectorizer,
                "tfidf_matrix": self.cbf_service.tfidf_matrix,
                "place_id_to_idx": self.cbf_service.place_id_to_idx,
                "idx_to_place_id": self.cbf_service.idx_to_place_id,
            },
            "apriori_state": {
                "rules": self.apriori_service.rules,
                "relative_support": self.apriori_service.relative_support,
            },
            "text_preprocessor_state": {
                "memoized_stems": getattr(self.text_preprocessor, "_memoized_stems", {}),
            },
        }

        temp_path = state_path.with_suffix(f"{state_path.suffix}.tmp")
        with temp_path.open("wb") as file_handle:
            pickle.dump(state, file_handle, protocol=pickle.HIGHEST_PROTOCOL)
        temp_path.replace(state_path)

    def load_state(self, filepath: str) -> None:
        self.logger.info("Loading recommendation state: path=%s", filepath)
        state_path = Path(filepath)
        if not state_path.exists():
            raise FileNotFoundError(str(state_path))

        with state_path.open("rb") as file_handle:
            state = pickle.load(file_handle)

        self._places_df = state.get("places_df", pd.DataFrame())
        self._interactions_df = state.get("interactions_df", pd.DataFrame())
        self._place_lookup = dict(state.get("place_lookup", {}))
        self._min_price = float(state.get("min_price", 0.0))
        self._max_price = float(state.get("max_price", 0.0))

        cbf_state = state.get("cbf_state", {})
        self.cbf_service.vectorizer = cbf_state.get("vectorizer")
        self.cbf_service.tfidf_matrix = cbf_state.get("tfidf_matrix")
        self.cbf_service.place_id_to_idx = dict(cbf_state.get("place_id_to_idx", {}))
        self.cbf_service.idx_to_place_id = dict(cbf_state.get("idx_to_place_id", {}))

        apriori_state = state.get("apriori_state", {})
        self.apriori_service.rules = apriori_state.get("rules", pd.DataFrame())
        self.apriori_service.relative_support = float(apriori_state.get("relative_support", 0.0))

        self.text_preprocessor = TextPreprocessor()
        self.text_preprocessor._memoized_stems = dict(state.get("text_preprocessor_state", {}).get("memoized_stems", {}))
        self._ready = True
        self.logger.info("Recommendation state loaded: places=%s interactions=%s", self.places_count, self.interactions_count)

    async def refresh(
        self,
        bundle: DataBundle | None = None,
    ) -> DataBundle:
        refresh_started = time.perf_counter()
        self.logger.info("Recommendation refresh started")
        bundle = bundle or await self.repository.refresh()

        preprocess_started = time.perf_counter()
        places_df = self.text_preprocessor.preprocess_places(bundle.places)
        self.logger.info(
            "Sastrawi/text preprocessing finished: places=%s memoizedStems=%s durationMs=%.2f",
            int(places_df.shape[0]),
            len(getattr(self.text_preprocessor, "_memoized_stems", {})),
            (time.perf_counter() - preprocess_started) * 1000,
        )

        if "placeId" not in places_df.columns:
            if "id" in places_df.columns:
                places_df["placeId"] = places_df["id"].fillna("").astype(str)
            else:
                raise ValueError("Places payload must include placeId.")

        places_df = places_df.copy()
        places_df["placeId"] = places_df["placeId"].fillna("").astype(str)
        for column in ("placePrice", "placeRating"):
            if column in places_df.columns:
                places_df[column] = pd.to_numeric(places_df[column], errors="coerce").fillna(0)
            else:
                places_df[column] = 0.0

        known_place_ids = set(places_df["placeId"].tolist())

        interaction_clean_started = time.perf_counter()
        interactions_df = self._clean_interactions(bundle.interactions, known_place_ids)
        self.logger.info(
            "Interactions cleaning finished: raw=%s cleaned=%s durationMs=%.2f",
            int(bundle.interactions.shape[0]),
            int(interactions_df.shape[0]),
            (time.perf_counter() - interaction_clean_started) * 1000,
        )

        self._places_df = places_df
        self._interactions_df = interactions_df
        self._place_lookup = self._build_place_lookup(places_df)
        self._min_price = float(places_df["placePrice"].min()) if not places_df.empty else 0.0
        self._max_price = float(places_df["placePrice"].max()) if not places_df.empty else 0.0

        cbf_fit_started = time.perf_counter()
        self.cbf_service.fit(places_df)
        self.logger.info(
            "CBF fit finished: places=%s durationMs=%.2f",
            int(places_df.shape[0]),
            (time.perf_counter() - cbf_fit_started) * 1000,
        )

        apriori_fit_started = time.perf_counter()
        self.apriori_service.fit(
            interactions_df,
            absolute_support=self.settings.apriori_absolute_support,
            max_len=self.settings.apriori_max_len,
            min_user_interactions=self.settings.apriori_min_user_interactions,
        )
        self.logger.info(
            "Apriori fit finished: interactions=%s rules=%s support=%.6f durationMs=%.2f",
            int(interactions_df.shape[0]),
            int(self.apriori_service.rules.shape[0]) if hasattr(self.apriori_service.rules, "shape") else 0,
            float(self.apriori_service.relative_support),
            (time.perf_counter() - apriori_fit_started) * 1000,
        )

        self._ready = True

        save_state_started = time.perf_counter()
        self.save_state(self.state_filepath)
        self.logger.info("State save finished: path=%s durationMs=%.2f", self.state_filepath, (time.perf_counter() - save_state_started) * 1000)

        self.logger.info(
            "Recommendation refresh finished: places=%s interactions=%s durationMs=%.2f",
            self.places_count,
            self.interactions_count,
            (time.perf_counter() - refresh_started) * 1000,
        )
        return bundle

    def _ensure_ready(self) -> None:
        if not self._ready:
            raise RuntimeError("Recommendation service is not ready. Call refresh first.")

    def _validate_request_ids(self, ids: Iterable[str]) -> list[str]:
        self._ensure_ready()
        normalized_ids = [str(item).strip() for item in ids if str(item).strip()]
        if not normalized_ids:
            raise ValueError("At least one place id is required.")

        if len(normalized_ids) > self.settings.max_user_basket_size:
            raise ValueError(f"Basket exceeds max size of {self.settings.max_user_basket_size}.")

        known_ids = set(self._places_df["placeId"].astype(str).tolist())
        unknown_ids = [place_id for place_id in normalized_ids if place_id not in known_ids]
        if unknown_ids:
            raise ValueError(f"Unknown place ids: {', '.join(sorted(set(unknown_ids)))}")
        return normalized_ids

    def _rank_with_sources(self, candidate_pool: list[str], source_map: dict[str, str], k: int) -> list[dict[str, object]]:
        ranked = self.mcrs_service.rank(candidate_pool, self._place_lookup, self._min_price, self._max_price, k)
        results: list[dict[str, object]] = []
        for index, item in enumerate(ranked, start=1):
            place_id = str(item.get("place_id", ""))
            score_val = float(cast(float, item.get("score", 0.0)))
            results.append(
                {
                    "place_id": place_id,
                    "score": score_val,
                    "rank": index,
                    "source": source_map.get(place_id, "unknown"),
                }
            )
        return results

    def _resolve_target_n(self, k: int) -> int:
        configured_n = getattr(self.settings, "mcrs_n_candidates", self.settings.default_candidate_overgenerate_n)
        return max(int(configured_n), int(k) * 2)

    @staticmethod
    def _extend_unique(base_candidates: list[str], new_candidates: Iterable[str], limit: int) -> None:
        seen = set(base_candidates)
        for candidate in new_candidates:
            candidate_id = str(candidate)
            if candidate_id in seen:
                continue
            base_candidates.append(candidate_id)
            seen.add(candidate_id)
            if len(base_candidates) >= limit:
                break

    def _cascade_candidates(
        self,
        seed_candidates: list[str],
        padding_candidates: Iterable[dict[str, object]],
        target_n: int,
        padding_source: str,
    ) -> tuple[list[str], dict[str, str]]:
        cascaded_candidates = seed_candidates[:target_n]
        source_map = {candidate: "apriori" for candidate in cascaded_candidates}

        if len(cascaded_candidates) < target_n:
            needed = target_n - len(cascaded_candidates)
            padding_ids = [str(candidate.get("place_id", "")) for candidate in padding_candidates if candidate.get("place_id")]
            padding_ids = padding_ids[:needed]
            self._extend_unique(cascaded_candidates, padding_ids, target_n)
            for candidate_id in padding_ids:
                source_map[candidate_id] = self._merge_source(source_map.get(candidate_id), padding_source)

        return cascaded_candidates[:target_n], source_map

    def recommend_user_to_item(self, basket_ids: Iterable[str], k: int | None = None) -> list[dict[str, object]]:
        basket = [str(item).strip() for item in basket_ids if str(item).strip()]
        if not basket:
            return []

        basket = self._validate_request_ids(basket)
        k = int(k or self.settings.default_recommendation_k)
        target_n = self._resolve_target_n(k)
        basket_set = set(basket)

        apriori_candidates = [item for item in self.apriori_service.get_candidates(basket) if item not in basket_set]
        apriori_candidates = apriori_candidates[:target_n]

        padding_candidates = self.cbf_service.recommend_by_centroid(
            basket,
            exclude_ids=set(apriori_candidates) | basket_set,
            needed=max(0, target_n - len(apriori_candidates)),
        )
        cascaded_candidates, source_map = self._cascade_candidates(
            apriori_candidates,
            padding_candidates,
            target_n,
            padding_source="cbf_centroid",
        )

        return self._rank_with_sources(cascaded_candidates, source_map, k)

    def recommend_item_to_item(self, anchor_id: str, k: int | None = None) -> list[dict[str, object]]:
        anchor = self._validate_request_ids([anchor_id])[0]
        k = int(k or self.settings.default_recommendation_k)
        target_n = self._resolve_target_n(k)

        apriori_candidates = [item for item in self.apriori_service.get_candidates([anchor]) if item != anchor]
        apriori_candidates = apriori_candidates[:target_n]

        padding_candidates = self.cbf_service.recommend_by_anchor(
            anchor,
            exclude_ids=set(apriori_candidates) | {anchor},
            needed=max(0, target_n - len(apriori_candidates)),
        )
        cascaded_candidates, source_map = self._cascade_candidates(
            apriori_candidates,
            padding_candidates,
            target_n,
            padding_source="cbf_anchor",
        )

        return self._rank_with_sources(cascaded_candidates, source_map, k)

    def health_snapshot(self) -> dict[str, object]:
        return {
            "ready": self.is_ready,
            "places_count": self.places_count,
            "interactions_count": self.interactions_count,
        }
