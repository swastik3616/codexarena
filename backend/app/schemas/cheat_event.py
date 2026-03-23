from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheatEventCreateRequest(BaseModel):
    attempt_id: str
    event_type: str
    details: str | None = None


class CheatEventResponse(BaseModel):
    id: str
    attempt_id: str
    event_type: str
    details: str | None = None
    created_at: datetime | None = None

