from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

requests_total = Counter("requests_total", "Total HTTP requests", ["method", "path", "status_code"])
execution_jobs_total = Counter("execution_jobs_total", "Total execution jobs", ["status"])
ai_evaluations_total = Counter("ai_evaluations_total", "Total AI evaluations", ["status"])
cheat_events_total = Counter("cheat_events_total", "Total cheat events", ["severity", "event_type"])

request_duration_seconds = Histogram("request_duration_seconds", "HTTP request latency seconds", ["method", "path"])
execution_duration_seconds = Histogram("execution_duration_seconds", "Execution job duration seconds", ["language"])
ai_duration_seconds = Histogram("ai_duration_seconds", "AI task duration seconds", ["task"])

websocket_connections_active = Gauge("websocket_connections_active", "Active websocket connections", ["role"])
container_pool_idle = Gauge("container_pool_idle", "Idle containers in pool", ["language"])
redis_queue_depth = Gauge("redis_queue_depth", "Redis queue depth", ["queue"])


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

