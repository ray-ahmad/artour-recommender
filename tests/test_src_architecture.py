import asyncio
import os
import pandas as pd
from fastapi.testclient import TestClient

from src.config.settings import Settings, get_settings
from src.entity.recommendation import DataBundle
from src.infrastructure.server.rest import create_app
from src.module.recommendation.repository import ArtourRepository
from src.module.recommendation.service import RecommendationService


class FakeRepository(ArtourRepository):
    def __init__(self, bundle: DataBundle) -> None:
        self.bundle = bundle

    async def refresh(self) -> DataBundle:
        return self.bundle


def build_bundle() -> DataBundle:
    places = pd.DataFrame(
        [
            {
                "placeId": "p1",
                "placeName": "Alpha Garden",
                "placeCategoryName": "Park",
                "placeDescription": "green open garden with flowers",
                "placeAddress": "Street A",
                "placeHashtags": "#garden #green",
                "placePrice": 10,
                "placeRating": 4.8,
            },
            {
                "placeId": "p2",
                "placeName": "Beta Museum",
                "placeCategoryName": "Museum",
                "placeDescription": "historic art collection and exhibition",
                "placeAddress": "Street B",
                "placeHashtags": "#museum #art",
                "placePrice": 20,
                "placeRating": 4.2,
            },
        ]
    )

    interactions = pd.DataFrame(
        [
            {"userId": "u1", "refId": "p1", "refModule": "PLACE", "type": "PLACE_LIKE", "value": 1, "createdAt": "2026-05-01T10:00:00Z"},
            {"userId": "u1", "refId": "p2", "refModule": "PLACE", "type": "PLACE_BOOKMARK", "value": 1, "createdAt": "2026-05-01T11:00:00Z"},
        ]
    )

    return DataBundle(places=places, interactions=interactions)


def build_service() -> RecommendationService:
    settings = Settings(
        places_url="http://localhost:8001/places",
        interactions_url="http://localhost:8001/user-interactions",
        apriori_absolute_support=3,
        apriori_max_len=3,
        default_recommendation_k=1,
        default_candidate_overgenerate_n=2,
    )
    service = RecommendationService(repository=FakeRepository(build_bundle()), settings=settings)
    asyncio.run(service.refresh())
    return service


def test_src_clean_architecture_direct_flow() -> None:
    app = create_app()
    app.state.recommendation_service = build_service()

    with TestClient(app) as client:
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["ready"] is True

        user_resp = client.post(
            "/recommend/user-to-item",
            json={"basketIds": ["p1"], "k": 1},
        )
        assert user_resp.status_code == 200
        assert user_resp.json()["data"]["mode"] == "user-to-item"
        assert len(user_resp.json()["data"]["recommendations"]) == 1
