from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExecutionResultResponse(BaseModel):
    attempt_id: str
    status: str
    output: str | None = None
    passed: int | None = None
    failed: int | None = None
    duration_ms: int | None = None
    created_at: datetime | None = None

