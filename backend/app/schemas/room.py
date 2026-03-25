from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RoomCreateRequest(BaseModel):
    title: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class RoomCreateResponse(BaseModel):
    room_id: str
    title: str
    join_link: str
    status: Literal["pending", "active", "completed", "archived"] = "pending"


class RoomCandidateItem(BaseModel):
    candidate_id: str
    name: str
    status: Literal["waiting", "coding", "submitted", "evaluated"] = "waiting"


class RoomDetailResponse(BaseModel):
    room: dict[str, Optional[object]]
    candidates: list[RoomCandidateItem]


class RoomListItem(BaseModel):
    room_id: str
    title: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    status: str
    join_link: Optional[str] = None


class RoomListResponse(BaseModel):
    items: list[RoomListItem]
    limit: int = Field(default=20, ge=1)
    offset: int = Field(default=0, ge=0)

