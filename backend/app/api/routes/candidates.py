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
from app.services.ai.question_generator import QuestionGenerator
from app.services.realtime.websocket_hub import broadcast_room_event


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


def _get_questions_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not configured")
    return client.table("questions")


def _get_attempts_table() -> Any:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not configured")
    return client.table("attempts")


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


def _rate_limit(redis_client: Any, key: str, *, limit: int, ttl_seconds: int) -> None:
    if not hasattr(redis_client, "incr"):
        return
    try:
        count = redis_client.incr(key)
        if count == 1 and hasattr(redis_client, "expire"):
            redis_client.expire(key, ttl_seconds)
        if count > limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        return


@router.get("/resolve/{join_token}")
def resolve_join_token(join_token: str) -> dict[str, str]:
    redis_client = get_redis_client()
    room_id = redis_client.get(f"join:{join_token}")
    if not room_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Join token not found")
    return {"room_id": str(room_id)}


@router.post("/{room_id}/join", response_model=CandidateJoinResponse)
async def join_room(
    room_id: str,
    payload: CandidateJoinRequest,
    request: Request,
) -> CandidateJoinResponse:
    redis_client = get_redis_client()

    # Rate limit: max 5 join attempts per IP per 10 minutes
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "unknown").split(",")[0].strip()
    rl_key = f"rl:join:{ip}"
    _rate_limit(redis_client, rl_key, limit=5, ttl_seconds=600)

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

    # Ensure room has question assignment.
    room_res2 = rooms.select("*").eq("id", room_id).single().execute()
    room2 = room_res2.data or room
    question_id = room2.get("question_id")
    question_row: dict[str, Any] | None = None
    if question_id:
        question_row = _get_questions_table().select("*").eq("id", str(question_id)).single().execute().data
    else:
        try:
            generated = await QuestionGenerator().generate(
                difficulty=str(room2.get("difficulty") or "medium"),
                topic_tags=[],
                language="python",
            )
        except Exception:
            generated = {
                "id": str(uuid.uuid4()),
                "title": "Two Sum",
                "description": "Given nums and target, return indices adding to target.",
                "difficulty": str(room2.get("difficulty") or "medium"),
                "topic_tags": ["arrays"],
                "examples": [],
                "hints": [],
                "test_cases": [],
                "validation_status": "validated",
                "generated_by": "manual",
            }
            _get_questions_table().insert(generated).execute()
        question_id = str(generated.get("id"))
        question_row = generated
        rooms.update({"question_id": question_id}).eq("id", room_id).execute()

    attempt_id = str(uuid.uuid4())
    _get_attempts_table().insert(
        {
            "id": attempt_id,
            "candidate_id": candidate_id,
            "question_id": question_id,
            "language": "python",
            "code_snapshot": "",
            "status": "running",
            "started_at": now,
            "finished_at": None,
        }
    ).execute()

    question_payload = {
        "question_id": str(question_id),
        "title": (question_row or {}).get("title"),
        "description": (question_row or {}).get("description"),
        "examples": (question_row or {}).get("examples", []),
        "hints": (question_row or {}).get("hints", []),
        "topic_tags": (question_row or {}).get("topic_tags", []),
        "difficulty": (question_row or {}).get("difficulty", room2.get("difficulty")),
    }

    await broadcast_room_event(
        room_id=str(room_id),
        payload={
            "type": "room.joined",
            "candidate": {"id": candidate_id, "name": payload.name, "status": "waiting"},
            "question": question_payload,
        },
        target_role="all",
    )

    return CandidateJoinResponse(
        candidate_id=candidate_id,
        candidate_token=candidate_token,
        attempt_id=attempt_id,
        question=question_payload,
        room={
            "id": str(room2.get("id")),
            "title": room2.get("title"),
            "difficulty": room2.get("difficulty"),
        },
    )

