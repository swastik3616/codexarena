from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: UUID
    title: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    topic_tags: list[str] = Field(default_factory=list)
    test_cases: list[Any] = Field(default_factory=list)
    validation_status: Optional[Literal["pending", "validated", "failed"]] = "pending"
    generated_by: Optional[Literal["ai", "manual"]] = "ai"
    created_at: Optional[datetime] = None

