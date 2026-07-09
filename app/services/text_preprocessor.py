from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os
import re
from typing import Iterable

import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


_PROCESS_STEMMER = None
_PROCESS_STOPWORDS: set[str] | None = None


def _init_stemming_worker(stopwords: tuple[str, ...]) -> None:
    global _PROCESS_STEMMER, _PROCESS_STOPWORDS
    _PROCESS_STEMMER = StemmerFactory().create_stemmer()
    _PROCESS_STOPWORDS = set(stopwords)


def _stem_word_worker(word: str) -> tuple[str, str]:
    if _PROCESS_STEMMER is None or _PROCESS_STOPWORDS is None:
        _init_stemming_worker(tuple(StopWordRemoverFactory().get_stop_words()))

    if not word or word in _PROCESS_STOPWORDS:
        return word, ""

    return word, _PROCESS_STEMMER.stem(word)


class TextPreprocessor:
    TEXT_COLUMNS = (
        "placeName",
        "placeCategoryName",
        "placeDescription",
        "placeAddress",
        "placeHashtags",
    )

    def __init__(self) -> None:
        self._stemmer = StemmerFactory().create_stemmer()
        self._stopwords = set(StopWordRemoverFactory().get_stop_words())
        self._memoized_stems: dict[str, str] = {}
        self._parallel_threshold = int(os.getenv("ARTOUR_STEMMING_PARALLEL_THRESHOLD", "300"))
        self._max_workers = max(1, int(os.getenv("ARTOUR_STEMMING_MAX_WORKERS", str(os.cpu_count() or 1))))

    def _clean_text(self, value: str) -> str:
        value = str(value).lower()
        value = re.sub(r"[^a-z\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _stem_word(self, word: str) -> str:
        if word not in self._memoized_stems:
            if not word or word in self._stopwords:
                self._memoized_stems[word] = ""
            else:
                self._memoized_stems[word] = self._stemmer.stem(word)
        return self._memoized_stems[word]

    def _parallel_stem_unknown_words(self, unknown_words: list[str]) -> None:
        if not unknown_words:
            return

        workers = min(self._max_workers, len(unknown_words))
        if workers <= 1 or len(unknown_words) < self._parallel_threshold:
            for word in unknown_words:
                self._memoized_stems[word] = self._stemmer.stem(word)
            return

        chunksize = max(1, len(unknown_words) // (workers * 4))
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_stemming_worker,
            initargs=(tuple(self._stopwords),),
            mp_context=multiprocessing.get_context("forkserver"),
        ) as executor:
            for word, stemmed in executor.map(_stem_word_worker, unknown_words, chunksize=chunksize):
                self._memoized_stems[word] = stemmed

    def preprocess_places(self, places_df: pd.DataFrame) -> pd.DataFrame:
        df = places_df.copy()
        if df.empty:
            df["clean_text"] = pd.Series(dtype=str)
            return df

        combined = df.reindex(columns=self.TEXT_COLUMNS, fill_value="").fillna("").astype(str).agg(" ".join, axis=1)
        clean_text = combined.map(self._clean_text)
        unique_words = {word for text in clean_text.tolist() for word in text.split() if word}

        unknown_words = [word for word in unique_words if word not in self._memoized_stems and word not in self._stopwords]
        self._parallel_stem_unknown_words(unknown_words)

        # Cache stopwords/empty tokens locally to avoid repeated checks in row mapping.
        for word in unique_words:
            if word not in self._memoized_stems:
                self._memoized_stems[word] = ""

        df["clean_text"] = clean_text.map(
            lambda text: " ".join(
                self._memoized_stems.get(word, "")
                for word in str(text).split()
                if self._memoized_stems.get(word, "")
            )
        )
        return df
