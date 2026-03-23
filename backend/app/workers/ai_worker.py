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

