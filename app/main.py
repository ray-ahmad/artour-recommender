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
from app.repositories.artour_repository import ArtourRepository
from app.services.recommendation_service import RecommendationService
from app.services.refresh_job import run_refresh_job
from app.services.refresh_webhook_client import RefreshWebhookClient

logger = logging.getLogger("uvicorn.error")


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
