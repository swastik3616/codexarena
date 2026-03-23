from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Coroutine, Optional

import redis

from arq.worker import RedisSettings

from app.core.config import settings
from app.db.database import get_supabase_client
from app.services.execution import runner


def get_redis_client() -> Any:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def execute_submission(ctx: Any, job_payload: dict[str, Any]) -> None:
    """
    ARQ worker function: execute a submission inside the secure execution engine.

    job_payload contains:
      { attempt_id, candidate_id, code, language, test_cases, room_id }
    """

    attempt_id = str(job_payload["attempt_id"])
    candidate_id = str(job_payload["candidate_id"])
    code = job_payload["code"]
    language = job_payload["language"]
    test_cases = job_payload["test_cases"]
    room_id = str(job_payload["room_id"])

    # Update status to running.
    job_id = getattr(ctx, "job_id", None) or job_payload.get("job_id")
    if job_id:
        redis_client = get_redis_client()
        redis_client.set(f"exec_job:{job_id}:status", "running")

    result = await runner.execute_code(code=code, language=language, test_cases=test_cases)

    # Write to execution_results table.
    client = get_supabase_client()
    if client is not None:
        try:
            client.table("execution_results").insert(
                {
                    "attempt_id": attempt_id,
                    "test_pass_count": int(result.get("pass_count", 0)),
                    "test_total": int(result.get("total", len(test_cases))),
                    "stdout": result.get("stdout"),
                    "stderr": result.get("stderr"),
                    "exit_code": result.get("exit_code"),
                    "wall_time_ms": result.get("wall_time_ms"),
                    "memory_kb": result.get("memory_kb"),
                    "timed_out": bool(result.get("timed_out", False)),
                }
            ).execute()
        except Exception:
            pass

    # Publish to room websocket channel for broadcast.
    try:
        redis_client = get_redis_client()
        redis_client.publish(
            f"room:{room_id}:execution",
            json.dumps(
                {
                    "room_id": room_id,
                    "attempt_id": attempt_id,
                    "candidate_id": candidate_id,
                    "result": result,
                }
            ),
        )
    except Exception:
        pass

    # Mark job complete in Redis.
    if job_id:
        try:
            redis_client = get_redis_client()
            redis_client.set(f"exec_job:{job_id}:status", "complete")
        except Exception:
            pass


class WorkerSettings:
    """
    Scaffold ARQ settings container.

    In a real deployment you'd create an arq Worker with:
      Worker(functions=WorkerSettings.functions, redis_settings=WorkerSettings.redis_settings, ...)
    """

    redis_settings: RedisSettings = RedisSettings(host="localhost", port=6379, database=0)
    functions = [execute_submission]

