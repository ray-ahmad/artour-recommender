from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, status

from app.api.dependencies import get_refresh_webhook_client, get_recommendation_service
from app.api.schemas.recommendation import RefreshAcceptedEnvelope, RefreshAcceptedResponse, RefreshTriggerRequest
from app.configs.settings import Settings, get_settings
from app.services.recommendation_service import RecommendationService
from app.services.refresh_job import run_refresh_job
from app.services.refresh_webhook_client import RefreshWebhookClient

router = APIRouter(tags=["admin"])
logger = logging.getLogger("uvicorn.error")


@router.post("/refresh", response_model=RefreshAcceptedEnvelope, status_code=status.HTTP_202_ACCEPTED)
async def refresh(
    background_tasks: BackgroundTasks,
    payload: RefreshTriggerRequest | None = Body(default=None),
    x_artour_refresh_token: str | None = Header(default=None, alias="X-ARTOUR-REFRESH-TRIGGER-TOKEN"),
    settings: Settings = Depends(get_settings),
    service: RecommendationService = Depends(get_recommendation_service),
    webhook_client: RefreshWebhookClient = Depends(get_refresh_webhook_client),
) -> RefreshAcceptedEnvelope:
    if settings.refresh_trigger_token and x_artour_refresh_token != settings.refresh_trigger_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    refresh_id = payload.refresh_id if payload and payload.refresh_id else str(uuid4())
    logger.info("Refresh accepted: refreshId=%s", refresh_id)
    background_tasks.add_task(run_refresh_job, service, webhook_client, refresh_id)

    return RefreshAcceptedEnvelope(
        data=RefreshAcceptedResponse(
            refresh_id=refresh_id,
            accepted_at=datetime.now(timezone.utc),
        )
    )
