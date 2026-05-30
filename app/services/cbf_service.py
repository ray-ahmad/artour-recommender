from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import issparse


class CBFService:
    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix = None
        self.place_id_to_idx: dict[str, int] = {}
        self.idx_to_place_id: dict[int, str] = {}

    def fit(self, places_df: pd.DataFrame) -> None:
        if places_df.empty:
            self.vectorizer = None
            self.tfidf_matrix = None
            self.place_id_to_idx = {}
            self.idx_to_place_id = {}
            return

        self.vectorizer = TfidfVectorizer()
        clean_text = places_df["clean_text"].fillna("").astype(str)
        self.tfidf_matrix = self.vectorizer.fit_transform(clean_text)
        place_ids = places_df["placeId"].fillna("").astype(str).tolist()
        self.place_id_to_idx = {place_id: idx for idx, place_id in enumerate(place_ids)}
        self.idx_to_place_id = {idx: place_id for place_id, idx in self.place_id_to_idx.items()}

    def _rank_similar(self, query_vector, exclude_ids: set[str], needed: int, source: str) -> list[dict[str, object]]:
        if self.tfidf_matrix is None or needed <= 0:
            return []

        if issparse(query_vector):
            query_matrix = query_vector
        else:
            query_matrix = np.asarray(query_vector)

        scores = cosine_similarity(query_matrix, self.tfidf_matrix).ravel()
        ranked_indices = scores.argsort()[::-1]
        results: list[dict[str, object]] = []

        for index in ranked_indices:
            place_id = self.idx_to_place_id.get(int(index))
            if not place_id or place_id in exclude_ids:
                continue
            results.append(
                {
                    "place_id": place_id,
                    "score": float(scores[int(index)]),
                    "source": source,
                }
            )
            if len(results) >= needed:
                break

        return results

    def recommend_by_centroid(self, basket_ids: Iterable[str], exclude_ids: Iterable[str] | None = None, needed: int = 10) -> list[dict[str, object]]:
        exclude_set = {str(item) for item in (exclude_ids or [])}
        basket_indices = [self.place_id_to_idx[str(place_id)] for place_id in basket_ids if str(place_id) in self.place_id_to_idx]
        if not basket_indices:
            return []

        centroid_vector = self.tfidf_matrix[basket_indices].mean(axis=0)
        return self._rank_similar(centroid_vector, exclude_set | {str(place_id) for place_id in basket_ids}, needed, "cbf_centroid")

    def recommend_by_anchor(self, anchor_id: str, exclude_ids: Iterable[str] | None = None, needed: int = 10) -> list[dict[str, object]]:
        exclude_set = {str(item) for item in (exclude_ids or [])}
        anchor_index = self.place_id_to_idx.get(str(anchor_id))
        if anchor_index is None:
            return []

        anchor_vector = self.tfidf_matrix[anchor_index]
        return self._rank_similar(anchor_vector, exclude_set | {str(anchor_id)}, needed, "cbf_anchor")
