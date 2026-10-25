from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _resolve_places_url() -> str:
    if os.getenv("ARTOUR_PLACES_URL"):
        return os.environ["ARTOUR_PLACES_URL"]
    base_url = os.getenv("ARTOUR_BACKEND_BASE_URL", "http://localhost:8001").rstrip("/")
    path = os.getenv("ARTOUR_PLACES_PATH", "/places").lstrip("/")
    return f"{base_url}/{path}"


def _resolve_interactions_url() -> str:
    if os.getenv("ARTOUR_INTERACTIONS_URL"):
        return os.environ["ARTOUR_INTERACTIONS_URL"]
    base_url = os.getenv("ARTOUR_BACKEND_BASE_URL", "http://localhost:8001").rstrip("/")
    path = os.getenv("ARTOUR_USER_INTERACTIONS_PATH", "/user-interactions").lstrip("/")
    return f"{base_url}/{path}"


def _resolve_state_filepath() -> str:
    default_cache = (
        "/tmp/recommendation_state.pkl"
        if os.getenv("SPACE_ID")
        else str(Path(__file__).resolve().parents[2] / ".cache" / "recommendation_state.pkl")
    )
    return os.getenv("ARTOUR_RECOMMENDATION_STATE_PATH", default_cache)


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: _env("ARTOUR_APP_NAME", "ARTour Recommender API"))
    places_url: str = field(default_factory=_resolve_places_url)
    interactions_url: str = field(default_factory=_resolve_interactions_url)
    state_filepath: str = field(default_factory=_resolve_state_filepath)
    refresh_webhook_url: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_WEBHOOK_URL", ""))
    refresh_webhook_token: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_WEBHOOK_TOKEN", ""))
    refresh_trigger_token: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_TRIGGER_TOKEN", ""))
    refresh_webhook_timeout_seconds: float = field(
        default_factory=lambda: _env_float("ARTOUR_REFRESH_WEBHOOK_TIMEOUT_SECONDS", "30")
    )
    request_timeout_seconds: float = field(
        default_factory=lambda: _env_float("ARTOUR_REQUEST_TIMEOUT_SECONDS", "15")
    )
    min_positive_rating: float = field(
        default_factory=lambda: _env_float("ARTOUR_MIN_POSITIVE_RATING", "4.0")
    )
    apriori_absolute_support: int = field(
        default_factory=lambda: _env_int("ARTOUR_APRIORI_ABSOLUTE_SUPPORT", "3")
    )
    apriori_min_user_interactions: int = field(
        default_factory=lambda: _env_int("ARTOUR_APRIORI_MIN_USER_INTERACTIONS", "2")
    )
    apriori_max_len: int = field(
        default_factory=lambda: _env_int("ARTOUR_APRIORI_MAX_LEN", "3")
    )
    mcrs_min_rating_scale: float = field(
        default_factory=lambda: _env_float("ARTOUR_MCRS_MIN_RATING_SCALE", "1.0")
    )
    mcrs_max_rating_scale: float = field(
        default_factory=lambda: _env_float("ARTOUR_MCRS_MAX_RATING_SCALE", "5.0")
    )
    mcrs_neutral_rating_score: float = field(
        default_factory=lambda: _env_float("ARTOUR_MCRS_NEUTRAL_RATING_SCORE", "0.5")
    )
    weight_cost: float = field(
        default_factory=lambda: _env_float("ARTOUR_WEIGHT_COST", "0.5")
    )
    weight_benefit: float = field(
        default_factory=lambda: _env_float("ARTOUR_WEIGHT_BENEFIT", "0.5")
    )
    default_recommendation_k: int = field(
        default_factory=lambda: _env_int("ARTOUR_DEFAULT_K", "10")
    )
    default_candidate_overgenerate_n: int = field(
        default_factory=lambda: _env_int("ARTOUR_DEFAULT_N", "20")
    )
    max_user_basket_size: int = field(
        default_factory=lambda: _env_int("ARTOUR_MAX_USER_BASKET_SIZE", "50")
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
