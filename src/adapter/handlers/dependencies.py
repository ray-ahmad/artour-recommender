from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status

from src.config.settings import Settings, get_settings
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


@dataclass(frozen=True)
class AdminDependencies:
    settings: Settings
    service: RecommendationService
    webhook_client: RefreshWebhookClient


def get_admin_dependencies(
    settings: Settings = Depends(get_settings),
    service: RecommendationService = Depends(get_recommendation_service),
    webhook_client: RefreshWebhookClient = Depends(get_refresh_webhook_client),
) -> AdminDependencies:
    return AdminDependencies(
        settings=settings,
        service=service,
        webhook_client=webhook_client,
    )


def verify_refresh_token(
    x_artour_refresh_token: str | None = Header(default=None, alias="X-ARTOUR-REFRESH-TRIGGER-TOKEN"),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.refresh_trigger_token and x_artour_refresh_token != settings.refresh_trigger_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
