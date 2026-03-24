from __future__ import annotations

import time
from uuid import uuid4
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
try:
    import structlog.contextvars as structlog_contextvars
except ModuleNotFoundError:  # pragma: no cover
    structlog_contextvars = None

from app.api.routes import analytics, auth, attempts, candidates, execute, questions, rooms
from app.api.routes import websocket as websocket_routes
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import metrics_response, request_duration_seconds, requests_total
from app.services.execution.pool import start_all_pools

configure_logging(service=settings.SERVICE_MODE or "api")
logger = get_logger()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        integrations=[FastApiIntegration(), LoggingIntegration(level=None, event_level=None)],
    )

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

mode = (settings.SERVICE_MODE or "api").strip().lower()
if mode == "websocket":
    app.include_router(websocket_routes.router)
elif mode == "api":
    app.include_router(auth.router)
    app.include_router(rooms.router)
    app.include_router(candidates.router)
    app.include_router(questions.router)
    app.include_router(execute.router)
    app.include_router(attempts.router)
    app.include_router(analytics.router)
    # API mode may still keep websocket route available for local all-in-one usage.
    app.include_router(websocket_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CodexArena Backend Running"}


@app.on_event("startup")
async def startup_event() -> None:
    # Pre-warm all execution pools (best-effort).
    if mode == "api":
        try:
            await start_all_pools()
        except Exception:
            # Keep API startup resilient even if Docker/image pull isn't available.
            pass


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    if structlog_contextvars is not None:
        structlog_contextvars.clear_contextvars()
        structlog_contextvars.bind_contextvars(
            request_id=request_id,
            user_id="-",
            service=settings.SERVICE_MODE or "api",
        )
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", method=request.method, path=request.url.path)
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    requests_total.labels(request.method, request.url.path, str(response.status_code)).inc()
    request_duration_seconds.labels(request.method, request.url.path).observe(duration_ms / 1000.0)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    if duration_ms > 2000:
        logger.warning("slow_request", method=request.method, path=request.url.path, duration_ms=duration_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

