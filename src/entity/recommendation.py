from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataBundle:
    places: pd.DataFrame
    interactions: pd.DataFrame


@dataclass(frozen=True)
class AprioriFitParams:
    absolute_support: int = 3
    max_len: int = 3
    min_user_interactions: int = 2


@dataclass(frozen=True)
class CBFRankParams:
    exclude_ids: set[str]
    needed: int
    source: str


@dataclass(frozen=True)
class MCRSRankParams:
    place_lookup: Mapping[str, dict[str, float]]
    min_price: float
    max_price: float
    limit: int


@dataclass(frozen=True)
class CascadePaddingParams:
    padding_candidates: list[dict[str, object]]
    target_n: int
    padding_source: str
