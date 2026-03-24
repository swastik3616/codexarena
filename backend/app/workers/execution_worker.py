from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Coroutine, Optional

import redis

from arq.worker import RedisSettings

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import execution_duration_seconds, execution_jobs_total
from app.db.database import get_supabase_client
logger = get_logger(service="execution_worker")

from app.services.ai.code_evaluator import CodeEvaluator
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
    logger.info("job_started", attempt_id=attempt_id, language=language, job_id=job_id or "-")
    start = time.perf_counter()

    result = await runner.execute_code(code=code, language=language, test_cases=test_cases)
    elapsed = max(0.0, time.perf_counter() - start)
    execution_duration_seconds.labels(language).observe(elapsed)

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
    execution_jobs_total.labels("completed").inc()
    logger.info(
        "job_completed",
        attempt_id=attempt_id,
        language=language,
        wall_time_ms=int(result.get("wall_time_ms", 0) or 0),
        pass_count=int(result.get("pass_count", 0) or 0),
    )

    # Chain AI evaluation after execution result is available.
    try:
        client = get_supabase_client()
        if client is not None:
            attempt = client.table("attempts").select("*").eq("id", attempt_id).single().execute().data or {}
            question_id = attempt.get("question_id")
            question = (
                client.table("questions").select("*").eq("id", question_id).single().execute().data
                if question_id
                else {}
            )
            execution_result = {
                "pass_count": int(result.get("pass_count", 0)),
                "total": int(result.get("total", len(test_cases))),
                "timed_out": bool(result.get("timed_out", False)),
            }
            await CodeEvaluator().evaluate(
                attempt_id=attempt_id,
                code=code,
                language=language,
                execution_result=execution_result,
                question=question or {},
            )
    except Exception:
        # Execution completion should not fail due to evaluator issues.
        logger.exception("execution_postprocess_failed", attempt_id=attempt_id)
        pass


class WorkerSettings:
    """
    Scaffold ARQ settings container.

    In a real deployment you'd create an arq Worker with:
      Worker(functions=WorkerSettings.functions, redis_settings=WorkerSettings.redis_settings, ...)
    """

    redis_settings: RedisSettings = RedisSettings(host="localhost", port=6379, database=0)
    functions = [execute_submission]


class ExecutionWorkerSettings(WorkerSettings):
    pass

