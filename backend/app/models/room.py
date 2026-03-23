from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class Room(BaseModel):
    id: UUID
    recruiter_id: UUID
    title: str
    status: Optional[Literal["pending", "active", "completed", "archived"]] = "pending"
    join_token: str
    question_id: Optional[UUID] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = "medium"
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

