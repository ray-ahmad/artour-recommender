from __future__ import annotations

import logging

import httpx

from app.api.schemas.recommendation import RefreshWebhookPayload
from app.configs.settings import Settings, get_settings


class RefreshWebhookClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("uvicorn.error")

    async def send(self, payload: RefreshWebhookPayload) -> None:
        webhook_url = self.settings.refresh_webhook_url
        if not webhook_url:
            self.logger.info("Refresh webhook URL is not configured; skipping callback for %s", payload.refresh_id)
            return

        headers: dict[str, str] = {}
        if self.settings.refresh_webhook_token:
            headers["X-ARTOUR-INTEGRATION-TOKEN"] = self.settings.refresh_webhook_token

        timeout = httpx.Timeout(self.settings.refresh_webhook_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(webhook_url, json=payload.model_dump(mode="json", by_alias=True), headers=headers)
            response.raise_for_status()
            self.logger.info("Refresh webhook delivered for %s with status %s", payload.refresh_id, response.status_code)