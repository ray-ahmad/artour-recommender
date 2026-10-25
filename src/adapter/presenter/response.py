from __future__ import annotations

from typing import Any
from fastapi.responses import JSONResponse


def build_error_response(message: str, error: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "error": error,
            "statusCode": status_code,
        },
    )


def build_success_response(data: Any, message: str = "success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": data,
            "statusCode": status_code,
        },
    )
