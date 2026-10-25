from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from http import HTTPStatus
import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config.settings import Settings, get_settings
from src.adapter.presenter.response import build_error_response
from src.adapter.routes.router import init_routes
from src.clients.webhook_client import RefreshWebhookClient
from src.infrastructure.middlewares.correlation_id import (
    CorrelationIdLogFilter,
    CorrelationIdMiddleware,
)
from src.module.recommendation.refresh_job import run_refresh_job
from src.module.recommendation.repository import ArtourRepository
from src.module.recommendation.service import RecommendationService

logger = logging.getLogger(__name__)

_APP_LOG_FORMAT = "%(asctime)s %(levelname)-8s [cid=%(correlation_id)s] %(name)s: %(message)s"


def configure_app_logging() -> None:
    uvicorn_error_logger = logging.getLogger("uvicorn.error")

    target_loggers = [
        __name__,
        "src.adapter.handlers.admin_handler",
        "src.module.recommendation.refresh_job",
        "src.module.recommendation.repository",
        "src.module.recommendation.service",
        "src.module.recommendation.algorithms.apriori",
        "src.module.recommendation.algorithms.cbf",
        "src.module.recommendation.algorithms.mcrs",
        "src.clients.webhook_client",
        "RecommendationService",
        "ArtourRepository",
        "RefreshWebhookClient",
    ]

    base_stream = getattr(uvicorn_error_logger.handlers[0], "stream", None) if uvicorn_error_logger.handlers else None
    app_handler = logging.StreamHandler(base_stream)
    app_handler.setFormatter(logging.Formatter(_APP_LOG_FORMAT))
    correlation_filter = CorrelationIdLogFilter()

    for logger_name in target_loggers:
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(logging.INFO)

        if app_handler not in app_logger.handlers:
            app_logger.addHandler(app_handler)
        if not any(isinstance(existing_filter, CorrelationIdLogFilter) for existing_filter in app_logger.filters):
            app_logger.addFilter(correlation_filter)
        app_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_app_logging()
    logger.info("App logging initialized")

    service = cast(RecommendationService, getattr(app.state, "recommendation_service", None))
    webhook_client = cast(RefreshWebhookClient, getattr(app.state, "refresh_webhook_client", None))
    if service is not None:
        try:
            service.load_state(service.state_filepath)
        except FileNotFoundError:
            logger.info("No persisted state found — triggering background refresh")
            asyncio.create_task(run_refresh_job(service, webhook_client))
        except Exception as exc:
            logger.info("No persisted recommendation state loaded: %s", exc)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    repository = ArtourRepository(resolved_settings)
    service = RecommendationService(repository=repository, settings=resolved_settings)
    webhook_client = RefreshWebhookClient(settings=resolved_settings)

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.recommendation_service = service
    app.state.refresh_webhook_client = webhook_client

    app.add_middleware(CorrelationIdMiddleware)

    # Register all routes from adapter
    app.include_router(init_routes())

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [str(item.get("msg", "Invalid request")) for item in exc.errors()]
        message = "; ".join(messages) if messages else "Invalid request"
        return build_error_response(message=message, error="Bad Request", status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        try:
            error_label = HTTPStatus(exc.status_code).phrase
        except ValueError:
            error_label = "HTTP Error"

        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return build_error_response(message=detail, error=error_label, status_code=exc.status_code)

    return app


app = create_app()
