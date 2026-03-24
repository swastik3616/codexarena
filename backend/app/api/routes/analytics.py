from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_supabase_client

router = APIRouter(tags=["analytics"])


def get_redis_client() -> Any:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _to_epoch_seconds(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        from datetime import datetime

        if isinstance(value, datetime):
            return int(value.timestamp())
        # Try ISO datetime string
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


@router.get("/attempts/{attempt_id}/snapshots")
def get_attempt_snapshots(
    attempt_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    attempt = client.table("attempts").select("*").eq("id", attempt_id).single().execute().data
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    candidate = client.table("candidates").select("*").eq("id", str(attempt.get("candidate_id"))).single().execute().data
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    room_id = str(candidate.get("room_id"))

    room = client.table("rooms").select("*").eq("id", room_id).single().execute().data
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if str(room.get("recruiter_id")) != str(current_user.get("id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    snapshots: list[dict[str, Any]] = []
    redis_client = get_redis_client()
    live = redis_client.zrange(f"room:{room_id}:snapshots", 0, -1, withscores=True) or []
    if live:
        for item, score in live:
            try:
                obj = json.loads(item)
                snapshots.append({"timestamp": int(obj.get("timestamp", int(score))), "code": obj.get("code", "")})
            except Exception:
                snapshots.append({"timestamp": int(score), "code": str(item)})
    else:
        key = attempt.get("s3_archive_key")
        if isinstance(key, str) and key:
            try:
                if key.endswith(".json") and Path(key).exists():
                    body = json.loads(Path(key).read_text(encoding="utf-8"))
                else:
                    body = {}
                snapshots = body.get("snapshots", []) if isinstance(body, dict) else []
            except Exception:
                snapshots = []

    if snapshots:
        base = int(snapshots[0].get("timestamp", 0))
        for s in snapshots:
            s["elapsed_seconds"] = int(s.get("timestamp", base)) - base

    cheat_events = client.table("cheat_events").select("*").eq("candidate_id", str(candidate.get("id"))).execute().data or []
    return {"snapshots": snapshots, "cheat_events": cheat_events}


@router.get("/rooms/{room_id}/analytics")
def get_room_analytics(
    room_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    room = client.table("rooms").select("*").eq("id", room_id).single().execute().data
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if str(room.get("recruiter_id")) != str(current_user.get("id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    question = None
    if room.get("question_id"):
        question = client.table("questions").select("*").eq("id", str(room.get("question_id"))).single().execute().data

    candidates = client.table("candidates").select("*").eq("room_id", room_id).execute().data or []
    candidate_rows: list[dict[str, Any]] = []

    for c in candidates:
        candidate_id = str(c.get("id"))
        attempts = client.table("attempts").select("*").eq("candidate_id", candidate_id).execute().data or []
        attempt = attempts[-1] if attempts else {}
        attempt_id = attempt.get("id")

        exec_row = None
        ai_row = None
        if attempt_id:
            exec_row = client.table("execution_results").select("*").eq("attempt_id", str(attempt_id)).single().execute().data
            ai_row = client.table("ai_evaluations").select("*").eq("attempt_id", str(attempt_id)).single().execute().data

        events = client.table("cheat_events").select("*").eq("candidate_id", candidate_id).execute().data or []
        high_count = sum(1 for e in events if str(e.get("severity", "")).lower() == "high")

        joined_at = _to_epoch_seconds(c.get("joined_at"))
        submitted_at = _to_epoch_seconds(c.get("submitted_at")) or _to_epoch_seconds(attempt.get("submitted_at"))
        time_to_submit = (submitted_at - joined_at) if (joined_at and submitted_at and submitted_at >= joined_at) else None

        candidate_rows.append(
            {
                "id": candidate_id,
                "attempt_id": str(attempt_id) if attempt_id else None,
                "name": c.get("name"),
                "status": c.get("status"),
                "scores": {
                    "correctness": int((ai_row or {}).get("correctness_score") or 0),
                    "efficiency": int((ai_row or {}).get("efficiency_score") or 0),
                    "readability": int((ai_row or {}).get("readability_score") or 0),
                    "edge_cases": int((ai_row or {}).get("edge_case_score") or 0),
                    "total": int((ai_row or {}).get("total_score") or 0),
                },
                "execution": {
                    "pass_count": int((exec_row or {}).get("test_pass_count") or 0),
                    "total": int((exec_row or {}).get("test_total") or 0),
                    "wall_time_ms": int((exec_row or {}).get("wall_time_ms") or 0),
                },
                "big_o_time": (ai_row or {}).get("big_o_time"),
                "big_o_space": (ai_row or {}).get("big_o_space"),
                "cheat_event_count": len(events),
                "high_severity_count": high_count,
                "time_to_first_submit_seconds": time_to_submit,
            }
        )

    return {
        "room": {
            "id": str(room.get("id")),
            "title": room.get("title"),
            "created_at": room.get("created_at"),
            "candidate_count": len(candidates),
        },
        "candidates": candidate_rows,
        "question": {
            "title": (question or {}).get("title"),
            "difficulty": (question or {}).get("difficulty"),
            "topic_tags": (question or {}).get("topic_tags", []),
        },
    }

