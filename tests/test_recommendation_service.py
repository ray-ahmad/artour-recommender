import pandas as pd
import asyncio

from app.configs.settings import Settings
from app.repositories.artour_repository import ArtourRepository, DataBundle
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


def test_repository_build_bundle_from_json_payloads() -> None:
    repository = ArtourRepository(Settings(backend_base_url="http://example.com"))
    bundle = repository.build_bundle_from_payloads(
        {"data": build_bundle().places.to_dict(orient="records")},
        {"results": build_bundle().interactions.to_dict(orient="records")},
    )

    assert bundle.places.shape[0] == 4
    assert bundle.interactions.shape[0] == 4
    assert "placeId" in bundle.places.columns
    assert "userId" in bundle.interactions.columns


def test_user_to_item_uses_centroid_padding_when_apriori_is_empty() -> None:
    service = build_service()
    recommendations = service.recommend_user_to_item(["p1", "p2"], k=2)

    assert len(recommendations) == 2
    assert all(item["source"] == "cbf_centroid" for item in recommendations)
    assert all(item["place_id"] not in {"p1", "p2"} for item in recommendations)


def test_item_to_item_uses_anchor_padding_when_apriori_is_empty() -> None:
    service = build_service()
    recommendations = service.recommend_item_to_item("p1", k=2)

    assert len(recommendations) == 2
    assert all(item["source"] == "cbf_anchor" for item in recommendations)
    assert all(item["place_id"] != "p1" for item in recommendations)
