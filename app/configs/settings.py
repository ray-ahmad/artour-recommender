from dataclasses import dataclass, field
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load .env file so environment variables defined there are available at runtime
load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: _env("ARTOUR_APP_NAME", "ARTour Recommender API"))
    backend_base_url: str = field(default_factory=lambda: _env("ARTOUR_BACKEND_BASE_URL", "http://localhost:8001"))
    places_path: str = field(default_factory=lambda: _env("ARTOUR_PLACES_PATH", "/places"))
    interactions_path: str = field(default_factory=lambda: _env("ARTOUR_USER_INTERACTIONS_PATH", "/user-interactions"))
    refresh_webhook_url: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_WEBHOOK_URL", ""))
    refresh_webhook_token: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_WEBHOOK_TOKEN", ""))
    refresh_trigger_token: str = field(default_factory=lambda: _env("ARTOUR_REFRESH_TRIGGER_TOKEN", ""))
    refresh_webhook_timeout_seconds: float = field(default_factory=lambda: _env_float("ARTOUR_REFRESH_WEBHOOK_TIMEOUT_SECONDS", "30"))
    request_timeout_seconds: float = field(default_factory=lambda: _env_float("ARTOUR_REQUEST_TIMEOUT_SECONDS", "15"))
    min_positive_rating: float = field(default_factory=lambda: _env_float("ARTOUR_MIN_POSITIVE_RATING", "4.0"))
    apriori_absolute_support: int = field(default_factory=lambda: _env_int("ARTOUR_APRIORI_ABSOLUTE_SUPPORT", "3"))
    apriori_max_len: int = field(default_factory=lambda: _env_int("ARTOUR_APRIORI_MAX_LEN", "3"))
    mcrs_min_rating_scale: float = field(default_factory=lambda: _env_float("ARTOUR_MCRS_MIN_RATING_SCALE", "1.0"))
    mcrs_max_rating_scale: float = field(default_factory=lambda: _env_float("ARTOUR_MCRS_MAX_RATING_SCALE", "5.0"))
    weight_cost: float = field(default_factory=lambda: _env_float("ARTOUR_WEIGHT_COST", "0.5"))
    weight_benefit: float = field(default_factory=lambda: _env_float("ARTOUR_WEIGHT_BENEFIT", "0.5"))
    default_recommendation_k: int = field(default_factory=lambda: _env_int("ARTOUR_DEFAULT_K", "10"))
    default_candidate_overgenerate_n: int = field(default_factory=lambda: _env_int("ARTOUR_DEFAULT_N", "20"))
    max_user_basket_size: int = field(default_factory=lambda: _env_int("ARTOUR_MAX_USER_BASKET_SIZE", "50"))

    @property
    def backend_places_url(self) -> str:
        return f"{self.backend_base_url.rstrip('/')}/{self.places_path.lstrip('/')}"

    @property
    def backend_interactions_url(self) -> str:
        return f"{self.backend_base_url.rstrip('/')}/{self.interactions_path.lstrip('/')}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
