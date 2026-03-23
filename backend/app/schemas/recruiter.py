from __future__ import annotations

from pydantic import BaseModel, EmailStr


class RecruiterCreateRequest(BaseModel):
    email: EmailStr
    name: str | None = None


class RecruiterResponse(BaseModel):
    id: str
    email: EmailStr | None = None
    name: str | None = None

