from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


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

    def preprocess_places(self, places_df: pd.DataFrame) -> pd.DataFrame:
        df = places_df.copy()
        if df.empty:
            df["clean_text"] = pd.Series(dtype=str)
            return df

        combined = df.reindex(columns=self.TEXT_COLUMNS, fill_value="").fillna("").astype(str).agg(" ".join, axis=1)
        clean_text = combined.map(self._clean_text)
        unique_words = {word for text in clean_text.tolist() for word in text.split() if word}

        for word in unique_words:
            self._stem_word(word)

        df["clean_text"] = clean_text.map(
            lambda text: " ".join(
                stemmed
                for stemmed in (self._stem_word(word) for word in str(text).split())
                if stemmed
            )
        )
        return df
