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

