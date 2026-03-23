from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AIEvaluationResponse(BaseModel):
    attempt_id: str
    score: float | None = None
    feedback: str | None = None
    created_at: datetime | None = None

