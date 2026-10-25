from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass(frozen=True)
class DataBundle:
    places: pd.DataFrame
    interactions: pd.DataFrame
