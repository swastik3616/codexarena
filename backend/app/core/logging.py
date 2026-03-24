from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(service: str = "api") -> None:
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
    return structlog.get_logger().bind(**kwargs)

