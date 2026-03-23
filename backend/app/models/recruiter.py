from __future__ import annotations

from datetime import datetime
from typing import Literal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class Recruiter(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    company: Optional[str] = None
    plan: Optional[Literal["free", "pro", "enterprise"]] = "free"
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

