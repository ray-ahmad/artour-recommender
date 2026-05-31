from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from uuid import uuid4

from app.api.schemas.recommendation import RefreshWebhookPayload
from app.services.recommendation_service import RecommendationService
from app.services.refresh_webhook_client import RefreshWebhookClient

logger = logging.getLogger("uvicorn.error")


async def run_refresh_job(
    service: RecommendationService,
    webhook_client: RefreshWebhookClient,
    refresh_id: str | None = None,
) -> None:
    job_id = refresh_id or str(uuid4())
    status = "failed"
    error_message: str | None = None
    started_at = time.perf_counter()

    logger.info("Refresh job started: refreshId=%s", job_id)

    try:
        await service.refresh()
        status = "success"
        logger.info(
            "Refresh job succeeded: refreshId=%s places=%s interactions=%s",
            job_id,
            service.places_count,
            service.interactions_count,
        )
    except Exception as exc:
        error_message = str(exc)
        logger.exception("Refresh job %s failed", job_id)

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info("Refresh job finished: refreshId=%s status=%s durationMs=%s", job_id, status, elapsed_ms)

    payload = RefreshWebhookPayload(
        refresh_id=job_id,
        status=status,
        finished_at=datetime.now(timezone.utc),
        places_count=service.places_count if status == "success" else None,
        interactions_count=service.interactions_count if status == "success" else None,
        error=error_message,
    )

    try:
        await webhook_client.send(payload)
        logger.info("Refresh job webhook sent: refreshId=%s", job_id)
    except Exception as exc:
        logger.exception("Failed to deliver refresh webhook for %s: %s", job_id, exc)