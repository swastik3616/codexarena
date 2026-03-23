from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AttemptCreateRequest(BaseModel):
    candidate_id: str
    question_id: str


class AttemptResponse(BaseModel):
    id: str
    candidate_id: str
    question_id: str
    created_at: datetime | None = None
    submitted_at: datetime | None = None

