from __future__ import annotations

import contextvars
import logging

CORRELATION_ID_HEADER = "x-correlation-id"
_DEFAULT_CORRELATION_ID = "-"

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=_DEFAULT_CORRELATION_ID
)


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(value: str) -> contextvars.Token:
    return correlation_id_var.set(value)


def reset_correlation_id(token: contextvars.Token) -> None:
    correlation_id_var.reset(token)


class CorrelationIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True
