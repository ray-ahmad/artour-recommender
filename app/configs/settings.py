from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("ARTOUR_APP_NAME", "ARTour Recommender API")
    backend_base_url: str = os.getenv("ARTOUR_BACKEND_BASE_URL", "http://localhost:8001")
    places_path: str = os.getenv("ARTOUR_PLACES_PATH", "/places")
    interactions_path: str = os.getenv("ARTOUR_USER_INTERACTIONS_PATH", "/user-interactions")
    request_timeout_seconds: float = float(os.getenv("ARTOUR_REQUEST_TIMEOUT_SECONDS", "15"))
    min_positive_rating: float = float(os.getenv("ARTOUR_MIN_POSITIVE_RATING", "4.0"))
    apriori_absolute_support: int = int(os.getenv("ARTOUR_APRIORI_ABSOLUTE_SUPPORT", "3"))
    apriori_max_len: int = int(os.getenv("ARTOUR_APRIORI_MAX_LEN", "3"))
    mcrs_min_rating_scale: float = float(os.getenv("ARTOUR_MCRS_MIN_RATING_SCALE", "1.0"))
    mcrs_max_rating_scale: float = float(os.getenv("ARTOUR_MCRS_MAX_RATING_SCALE", "5.0"))
    weight_cost: float = float(os.getenv("ARTOUR_WEIGHT_COST", "0.5"))
    weight_benefit: float = float(os.getenv("ARTOUR_WEIGHT_BENEFIT", "0.5"))
    default_recommendation_k: int = int(os.getenv("ARTOUR_DEFAULT_K", "10"))
    default_candidate_overgenerate_n: int = int(os.getenv("ARTOUR_DEFAULT_N", "20"))
    max_user_basket_size: int = int(os.getenv("ARTOUR_MAX_USER_BASKET_SIZE", "50"))

    @property
    def backend_places_url(self) -> str:
        return f"{self.backend_base_url.rstrip('/')}/{self.places_path.lstrip('/')}"

    @property
    def backend_interactions_url(self) -> str:
        return f"{self.backend_base_url.rstrip('/')}/{self.interactions_path.lstrip('/')}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
