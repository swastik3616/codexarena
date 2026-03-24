from __future__ import annotations

import logging
import sys
from typing import Any
from types import SimpleNamespace

try:
    import structlog  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    structlog = None


class FallbackLogger:
    """
    Minimal structlog-like wrapper so the app can start without structlog installed.
    """

    def __init__(self, base: logging.Logger):
        self._base = base

    def bind(self, **_kwargs: Any) -> "FallbackLogger":
        return self

    def _log(self, level: str, event: str, **kwargs: Any) -> None:
        if kwargs:
            # Keep message short but debuggable.
            rendered = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
            msg = f"{event} | {rendered}"
        else:
            msg = event
        getattr(self._base, level)(msg)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log("info", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log("warning", event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        # exception() should include the traceback if one exists.
        if kwargs:
            self._base.exception(f"{event} | " + " ".join(f"{k}={v!r}" for k, v in kwargs.items()))
        else:
            self._base.exception(event)


_fallback_contextvars = SimpleNamespace(clear_contextvars=lambda: None, bind_contextvars=lambda **_kw: None)


def configure_logging(service: str = "api") -> None:
    if structlog is None:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        # If structlog isn't available, middleware/dependencies will no-op context binding.
        _fallback_contextvars.bind_contextvars(service=service, request_id="-", user_id="-")
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            timestamper,
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    structlog.contextvars.bind_contextvars(service=service, request_id="-", user_id="-")


def get_logger(**kwargs: Any):
    if structlog is None:
        return FallbackLogger(logging.getLogger("codexarena")).bind(**kwargs)
    return structlog.get_logger().bind(**kwargs)

