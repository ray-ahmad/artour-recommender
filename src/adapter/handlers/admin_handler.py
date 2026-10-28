from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, status

from src.adapter.handlers.dependencies import (
    AdminDependencies,
    get_admin_dependencies,
    verify_refresh_token,
)
from src.adapter.presenter.admin import (
    RefreshAcceptedEnvelopeOutput,
    RefreshAcceptedOutput,
    RefreshTriggerInput,
)
from src.module.recommendation.refresh_job import run_refresh_job

router = APIRouter(tags=["admin"])
logger = logging.getLogger("uvicorn.error")


@router.post(
    "/refresh",
    response_model=RefreshAcceptedEnvelopeOutput,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_refresh_token)],
)
async def refresh(
    background_tasks: BackgroundTasks,
    payload: RefreshTriggerInput | None = Body(default=None),
    deps: AdminDependencies = Depends(get_admin_dependencies),
) -> RefreshAcceptedEnvelopeOutput:
    refresh_id = payload.refresh_id if payload and payload.refresh_id else str(uuid4())
    logger.info("Refresh accepted: refreshId=%s", refresh_id)
    background_tasks.add_task(run_refresh_job, deps.service, deps.webhook_client, refresh_id)

    return RefreshAcceptedEnvelopeOutput(
        data=RefreshAcceptedOutput(
            refresh_id=refresh_id,
            accepted_at=datetime.now(timezone.utc),
        )
    )
