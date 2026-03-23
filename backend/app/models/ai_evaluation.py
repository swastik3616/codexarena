from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, conint


class AIEvaluation(BaseModel):
    id: UUID
    attempt_id: UUID
    correctness_score: conint(ge=0, le=40) = 0
    efficiency_score: conint(ge=0, le=30) = 0
    readability_score: conint(ge=0, le=20) = 0
    edge_case_score: conint(ge=0, le=10) = 0
    total_score: Optional[conint(ge=0, le=100)] = None
    big_o_time: Optional[str] = None
    big_o_space: Optional[str] = None
    feedback: Optional[str] = None
    suggestions: list[Any] = Field(default_factory=list)
    prompt_version: Optional[str] = "v1"
    evaluated_at: Optional[datetime] = None

