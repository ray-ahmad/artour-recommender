from contextlib import asynccontextmanager
import asyncio
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi import FastAPI

from app.api.routers.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.api.routers.recommendations import router as recommendations_router
from app.configs.settings import get_settings
from app.core.correlation import CorrelationIdLogFilter
from app.middlewares.correlation_id import CorrelationIdMiddleware
from app.repositories.artour_repository import ArtourRepository
from app.services.recommendation_service import RecommendationService
from app.services.refresh_job import run_refresh_job
from app.services.refresh_webhook_client import RefreshWebhookClient

logger = logging.getLogger(__name__)

_APP_LOG_FORMAT = "%(asctime)s %(levelname)-8s [cid=%(correlation_id)s] %(name)s: %(message)s"

# logging dengan correlation-id
def _configure_app_logging() -> None:
    uvicorn_error_logger = logging.getLogger("uvicorn.error")

    target_loggers = [
        __name__,
        "app.api.routers.admin",
        "app.services.refresh_job",
        "app.repositories.artour_repository",
        "app.services.recommendation_service",
        "app.services.apriori_service",
        "app.services.cbf_service",
        "app.services.mcrs_service",
        "app.services.refresh_webhook_client",
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


def _build_error_response(message: str, error: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "error": error,
            "statusCode": status_code,
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_app_logging()
    logger.info("App logging initialized")

    service = app.state.recommendation_service
    webhook_client = app.state.refresh_webhook_client
    try:
        service.load_state(service.state_filepath)
    except FileNotFoundError:
        logger.info("No persisted state found — triggering background refresh")
        asyncio.create_task(run_refresh_job(service, webhook_client))
    except Exception as exc:
        logger.info("No persisted recommendation state loaded: %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    repository = ArtourRepository(settings)
    service = RecommendationService(repository=repository, settings=settings)
    webhook_client = RefreshWebhookClient(settings=settings)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.recommendation_service = service
    app.state.refresh_webhook_client = webhook_client

    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(recommendations_router)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [str(item.get("msg", "Invalid request")) for item in exc.errors()]
        message = "; ".join(messages) if messages else "Invalid request"
        return _build_error_response(message=message, error="Bad Request", status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        try:
            error_label = HTTPStatus(exc.status_code).phrase
        except ValueError:
            error_label = "HTTP Error"

        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _build_error_response(message=detail, error=error_label, status_code=exc.status_code)

    return app


app = create_app()
