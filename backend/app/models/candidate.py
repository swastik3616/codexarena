from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class Candidate(BaseModel):
    id: UUID
    room_id: UUID
    name: str
    email: Optional[EmailStr] = None
    status: Optional[Literal["waiting", "coding", "submitted", "evaluated"]] = "waiting"
    joined_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None

