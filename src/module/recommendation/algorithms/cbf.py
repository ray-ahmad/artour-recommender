from __future__ import annotations

import logging
from typing import Iterable, cast

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import issparse, csr_matrix

from src.entity.recommendation import CBFRankParams

logger = logging.getLogger(__name__)


class CBFService:
    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix: csr_matrix | None = None
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
        self.tfidf_matrix = cast(csr_matrix, self.vectorizer.fit_transform(clean_text))
        place_ids = places_df["placeId"].fillna("").astype(str).tolist()
        self.place_id_to_idx = {place_id: idx for idx, place_id in enumerate(place_ids)}
        self.idx_to_place_id = {idx: place_id for place_id, idx in self.place_id_to_idx.items()}

    def recommend_by_centroid(self, basket_ids: Iterable[str], exclude_ids: Iterable[str] | None = None, needed: int = 10) -> list[dict[str, object]]:
        exclude_set = {str(item) for item in (exclude_ids or [])}
        basket_indices = [self.place_id_to_idx[str(place_id)] for place_id in basket_ids if str(place_id) in self.place_id_to_idx]
        if not basket_indices:
            return []

        tfidf = self.tfidf_matrix
        if tfidf is None:
            return []

        dense_rows = []
        for idx in basket_indices:
            try:
                row = tfidf.getrow(int(idx))
            except Exception:
                tocsr = getattr(tfidf, "tocsr", None)
                if callable(tocsr):
                    csr = cast(csr_matrix, tocsr())
                    row = csr.getrow(int(idx))
                else:
                    row = tfidf.getrow(int(idx))

            if hasattr(row, "toarray"):
                dense_rows.append(row.toarray().ravel())
            else:
                dense_rows.append(np.asarray(row).ravel())

        if not dense_rows:
            return []

        dense_subset = np.vstack(dense_rows)
        centroid_vector = np.atleast_2d(dense_subset.mean(axis=0).astype(float))
        params = CBFRankParams(
            exclude_ids=exclude_set | {str(place_id) for place_id in basket_ids},
            needed=needed,
            source="cbf_centroid",
        )
        return self._rank_similar(centroid_vector, params)

    def recommend_by_anchor(self, anchor_id: str, exclude_ids: Iterable[str] | None = None, needed: int = 10) -> list[dict[str, object]]:
        exclude_set = {str(item) for item in (exclude_ids or [])}
        anchor_index = self.place_id_to_idx.get(str(anchor_id))
        if anchor_index is None:
            return []

        tfidf = self.tfidf_matrix
        if tfidf is None:
            return []

        try:
            row = tfidf.getrow(int(anchor_index))
        except Exception:
            tocsr = getattr(tfidf, "tocsr", None)
            if callable(tocsr):
                csr = cast(csr_matrix, tocsr())
                row = csr.getrow(int(anchor_index))
            else:
                row = tfidf.getrow(int(anchor_index))

        if hasattr(row, "toarray"):
            anchor_vector = np.atleast_2d(row.toarray().astype(float))
        else:
            anchor_vector = np.atleast_2d(np.asarray(row).astype(float))

        params = CBFRankParams(
            exclude_ids=exclude_set | {str(anchor_id)},
            needed=needed,
            source="cbf_anchor",
        )
        return self._rank_similar(anchor_vector, params)

    def _rank_similar(self, query_vector: csr_matrix | np.ndarray, params: CBFRankParams) -> list[dict[str, object]]:
        tfidf = self.tfidf_matrix
        if tfidf is None or params.needed <= 0:
            return []

        if issparse(query_vector):
            query_matrix = query_vector
        else:
            query_matrix = np.asarray(query_vector)

        scores = cosine_similarity(query_matrix, tfidf).ravel()
        ranked_indices = scores.argsort()[::-1]
        results: list[dict[str, object]] = []

        for index in ranked_indices:
            place_id = self.idx_to_place_id.get(int(index))
            if not place_id or place_id in params.exclude_ids:
                continue
            results.append(
                {
                    "place_id": place_id,
                    "score": float(scores[int(index)]),
                    "source": params.source,
                }
            )
            if len(results) >= params.needed:
                break

        logger.info(
            "CBF fallback scoring: source=%s needed=%s excluded=%s matched=%s topScore=%.4f",
            params.source,
            params.needed,
            len(params.exclude_ids),
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results
