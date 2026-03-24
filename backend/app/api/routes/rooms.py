from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import get_current_candidate_or_recruiter, get_current_user
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.db.database import get_supabase_client
from app.schemas.room import RoomCreateRequest, RoomCreateResponse, RoomDetailResponse, RoomListResponse
from app.services.realtime.websocket_hub import archive_room_snapshots

router = APIRouter(prefix="/rooms", tags=["rooms"])

JOIN_LINK_BASE = "https://app.codexarena.io/join"


def _get_rooms_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return client.table("rooms")


def _get_candidates_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return client.table("candidates")


@router.post("", response_model=RoomCreateResponse)
def create_room(
    payload: RoomCreateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RoomCreateResponse:
    recruiter_id = current_user["id"]

    room_id = str(uuid.uuid4())
    timestamp = str(int(time.time()))

    secret = settings.JWT_SECRET_KEY.encode("utf-8")
    msg = (room_id + timestamp).encode("utf-8")
    join_token = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    join_link = f"{JOIN_LINK_BASE}/{join_token}"

    # Store join token mapping for 24 hours
    redis_client = get_redis_client()
    redis_client.set(f"join:{join_token}", room_id, ex=86400)

    now = datetime.now(timezone.utc)
    rooms = _get_rooms_table()
    rooms.insert(
        {
            "id": room_id,
            "recruiter_id": recruiter_id,
            "title": payload.title,
            "status": "pending",
            "join_token": join_token,
            "difficulty": payload.difficulty,
            "created_at": now,
            "started_at": None,
            "ended_at": None,
        }
    ).execute()

    return RoomCreateResponse(room_id=room_id, title=payload.title, join_link=join_link, status="pending")


@router.get("", response_model=RoomListResponse)
def list_rooms(
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RoomListResponse:
    recruiter_id = current_user["id"]
    rooms = _get_rooms_table()

    res = rooms.select("*").eq("recruiter_id", recruiter_id).execute()
    all_rows = res.data or []

    limit = 20
    sliced = all_rows[offset : offset + limit]

    items = [
        {
            "room_id": str(r.get("id")),
            "title": r.get("title"),
            "difficulty": r.get("difficulty"),
            "status": r.get("status"),
        }
        for r in sliced
    ]

    return RoomListResponse(items=items, limit=limit, offset=offset)


@router.get("/{room_id}", response_model=RoomDetailResponse)
def get_room_detail(
    room_id: str,
    current_user: dict[str, Any] = Depends(get_current_candidate_or_recruiter),
) -> RoomDetailResponse:
    rooms = _get_rooms_table()
    candidates = _get_candidates_table()

    room_res = rooms.select("*").eq("id", room_id).single().execute()
    room = room_res.data
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if current_user.get("role") == "candidate":
        candidate_row = candidates.select("*").eq("id", current_user["id"]).single().execute().data
        if not candidate_row or str(candidate_row.get("room_id")) != room_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    else:
        recruiter_id = current_user["id"]
        if str(room.get("recruiter_id")) != recruiter_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    cand_res = candidates.select("*").eq("room_id", room_id).execute()
    cand_rows = cand_res.data or []

    return RoomDetailResponse(
        room={
            "room_id": str(room.get("id")),
            "title": room.get("title"),
            "difficulty": room.get("difficulty"),
            "status": room.get("status"),
            "ended_at": room.get("ended_at"),
            "started_at": room.get("started_at"),
        },
        candidates=[
            {
                "candidate_id": str(c.get("id")),
                "name": c.get("name"),
                "status": c.get("status"),
            }
            for c in cand_rows
        ],
    )


@router.delete("/{room_id}")
async def archive_room(
    room_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    recruiter_id = current_user["id"]
    rooms = _get_rooms_table()

    room_res = rooms.select("*").eq("id", room_id).single().execute()
    room = room_res.data
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if str(room.get("recruiter_id")) != recruiter_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    now = datetime.now(timezone.utc)
    rooms.update({"status": "completed", "ended_at": now}).eq("id", room_id).execute()
    try:
        client = get_supabase_client()
        attempt_id: str | None = None
        if client is not None:
            candidates = client.table("candidates").select("*").eq("room_id", room_id).execute().data or []
            if candidates:
                candidate_id = str(candidates[-1].get("id"))
                attempts = client.table("attempts").select("*").eq("candidate_id", candidate_id).execute().data or []
                if attempts:
                    attempt_id = str(attempts[-1].get("id"))
        await archive_room_snapshots(room_id, attempt_id)
    except Exception:
        pass
    return {"message": "Room completed"}
