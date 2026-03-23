from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RecruiterAuthResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    recruiter: RecruiterAuthResponse

