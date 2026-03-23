from __future__ import annotations

from pydantic import BaseModel


class QuestionCreateRequest(BaseModel):
    prompt: str
    difficulty: str | None = None


class QuestionResponse(BaseModel):
    id: str
    prompt: str
    difficulty: str | None = None

