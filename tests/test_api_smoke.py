import pandas as pd
import asyncio
from fastapi.testclient import TestClient

from app.configs.settings import Settings
from app.main import create_app
from app.repositories.artour_repository import DataBundle
from app.services.recommendation_service import RecommendationService


class FakeRepository:
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
            {
                "placeId": "p3",
                "placeName": "Gamma Park",
                "placeCategoryName": "Park",
                "placeDescription": "open garden with trees and fresh air",
                "placeAddress": "Street C",
                "placeHashtags": "#park #nature",
                "placePrice": 12,
                "placeRating": 4.5,
            },
            {
                "placeId": "p4",
                "placeName": "Delta Cafe",
                "placeCategoryName": "Cafe",
                "placeDescription": "cozy coffee shop and pastry",
                "placeAddress": "Street D",
                "placeHashtags": "#cafe #coffee",
                "placePrice": 8,
                "placeRating": 4.0,
            },
        ]
    )

    interactions = pd.DataFrame(
        [
            {"userId": "u1", "refId": "p1", "refModule": "PLACE", "type": "PLACE_LIKE", "value": 1, "createdAt": "2026-05-01T10:00:00Z"},
            {"userId": "u1", "refId": "p2", "refModule": "PLACE", "type": "PLACE_BOOKMARK", "value": 1, "createdAt": "2026-05-01T11:00:00Z"},
            {"userId": "u2", "refId": "p1", "refModule": "PLACE", "type": "PLACE_REVIEW", "value": 5, "createdAt": "2026-05-02T10:00:00Z"},
            {"userId": "u2", "refId": "p3", "refModule": "PLACE", "type": "PLACE_LIKE", "value": 1, "createdAt": "2026-05-02T11:00:00Z"},
        ]
    )

    return DataBundle(places=places, interactions=interactions)


def build_service() -> RecommendationService:
    settings = Settings(
        backend_base_url="http://localhost:8001",
        apriori_absolute_support=3,
        apriori_max_len=3,
        default_recommendation_k=2,
        default_candidate_overgenerate_n=2,
    )
    service = RecommendationService(repository=FakeRepository(build_bundle()), settings=settings)
    asyncio.run(service.refresh())
    return service


def test_api_smoke_recommendations() -> None:
    app = create_app()
    app.state.recommendation_service = build_service()

    with TestClient(app) as client:
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["ready"] is True

        user_response = client.post(
            "/recommend/user-to-item",
            json={"basket_ids": ["p1", "p2"], "k": 2},
        )
        assert user_response.status_code == 200
        assert user_response.json()["data"]["mode"] == "user-to-item"
        assert len(user_response.json()["data"]["recommendations"]) == 2

        item_response = client.get("/recommend/item-to-item/p1", params={"k": 2})
        assert item_response.status_code == 200
        assert item_response.json()["data"]["mode"] == "item-to-item"
        assert len(item_response.json()["data"]["recommendations"]) == 2
