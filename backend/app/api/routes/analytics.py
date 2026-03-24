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

