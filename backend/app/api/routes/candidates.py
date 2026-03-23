from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt

from app.core.config import settings
from app.db.database import get_supabase_client
from app.schemas.candidate import CandidateJoinRequest, CandidateJoinResponse


router = APIRouter(prefix="/rooms", tags=["candidates"])


def get_redis_client() -> Any:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_rooms_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not configured")
    return client.table("rooms")


def _get_candidates_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not configured")
    return client.table("candidates")


def _create_candidate_token(*, candidate_id: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=4)
    payload = {
        "sub": candidate_id,
        "email": "",
        "jti": str(uuid.uuid4()),
        "role": "candidate",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


@router.post("/{room_id}/join", response_model=CandidateJoinResponse)
def join_room(
    room_id: str,
    payload: CandidateJoinRequest,
    request: Request,
) -> CandidateJoinResponse:
    redis_client = get_redis_client()

    # Rate limit: max 5 join attempts per IP per 10 minutes
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "unknown").split(",")[0].strip()
    rl_key = f"rl:join:{ip}"
    count = redis_client.incr(rl_key)
    if count == 1:
        redis_client.expire(rl_key, 600)  # 10 min window
    if count > 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    join_key = f"join:{payload.join_token}"
    joined_room_id = redis_client.get(join_key)
    if not joined_room_id or str(joined_room_id) != str(room_id):
        # Missing/expired token or token used for a different room.
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Join token expired or invalid")

    # Single-use token: delete mapping
    redis_client.delete(join_key)

    now = datetime.now(timezone.utc)

    candidates = _get_candidates_table()
    candidate_row = (
        candidates.insert(
            {
                "id": str(uuid.uuid4()),
                "room_id": room_id,
                "name": payload.name,
                "email": None,
                "status": "waiting",
                "joined_at": now,
                "submitted_at": None,
            }
        )
        .execute()
        .data
    )
    candidate_id = str(candidate_row[0]["id"])

    # Update room status pending -> active on first candidate join
    rooms = _get_rooms_table()
    room_res = rooms.select("*").eq("id", room_id).single().execute()
    room = room_res.data
    if room and room.get("status") == "pending":
        rooms.update({"status": "active", "started_at": now}).eq("id", room_id).execute()

    # Candidate token (4 hours, role=candidate)
    candidate_token = _create_candidate_token(candidate_id=candidate_id)

    # Return room snapshot
    room_res2 = rooms.select("*").eq("id", room_id).single().execute()
    room2 = room_res2.data or room
    return CandidateJoinResponse(
        candidate_id=candidate_id,
        candidate_token=candidate_token,
        room={
            "id": str(room2.get("id")),
            "title": room2.get("title"),
            "difficulty": room2.get("difficulty"),
        },
    )

