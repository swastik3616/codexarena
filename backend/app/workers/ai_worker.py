from __future__ import annotations

from typing import Any

from arq.worker import RedisSettings

from app.services.ai.code_evaluator import CodeEvaluator


async def evaluate_code(ctx: Any, payload: dict[str, Any]) -> dict[str, Any]:
    evaluator = CodeEvaluator()
    return await evaluator.evaluate(
        attempt_id=str(payload["attempt_id"]),
        code=str(payload["code"]),
        language=str(payload["language"]),
        execution_result=payload["execution_result"],
        question=payload["question"],
    )


class AIWorkerSettings:
    redis_settings: RedisSettings = RedisSettings(host="localhost", port=6379, database=0)
    functions = [evaluate_code]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AIJob:
    attempt_id: str
    payload: dict[str, Any]


async def perform(job: AIJob) -> dict[str, Any]:
    """
    Stub AI evaluation worker.

    The real implementation would call an LLM to evaluate submissions.
    """

    return {
        "attempt_id": job.attempt_id,
        "status": "not_implemented",
    }

