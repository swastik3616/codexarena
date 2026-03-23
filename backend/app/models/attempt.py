from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class Attempt(BaseModel):
    id: UUID
    candidate_id: UUID
    question_id: UUID
    language: Literal["python", "javascript", "java", "cpp", "go"] = "python"
    final_code: Optional[str] = None
    s3_archive_key: Optional[str] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None

