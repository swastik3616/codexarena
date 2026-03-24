from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CandidateJoinRequest(BaseModel):
    name: str
    join_token: str


class CandidateRoomSnapshot(BaseModel):
    id: str
    title: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class CandidateJoinResponse(BaseModel):
    candidate_id: str
    candidate_token: str
    attempt_id: str | None = None
    question: dict | None = None
    room: CandidateRoomSnapshot

