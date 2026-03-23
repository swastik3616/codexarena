from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheatEvent(BaseModel):
    id: UUID
    candidate_id: UUID
    event_type: Literal[
        "tab_switch",
        "large_paste",
        "face_absent",
        "multi_face",
        "idle_timeout",
        "copy_detected",
        "keystroke_anomaly",
        "solution_similarity",
    ]
    severity: Literal["low", "medium", "high"]
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None

