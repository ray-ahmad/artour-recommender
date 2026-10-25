from __future__ import annotations

from fastapi import Request

from src.clients.webhook_client import RefreshWebhookClient
from src.module.recommendation.service import RecommendationService


def get_recommendation_service(request: Request) -> RecommendationService:
    service = getattr(request.app.state, "recommendation_service", None)
    if service is None:
        raise RuntimeError("Recommendation service is not initialized.")
    return service


def get_refresh_webhook_client(request: Request) -> RefreshWebhookClient:
    webhook_client = getattr(request.app.state, "refresh_webhook_client", None)
    if webhook_client is None:
        raise RuntimeError("Refresh webhook client is not initialized.")
    return webhook_client
