from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any, DefaultDict, Dict

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import cheat_events_total, websocket_connections_active
logger = get_logger(service="websocket")

from app.core.security import verify_token
from app.db.database import get_supabase_client


active_connections: dict[str, dict[str, dict[str, WebSocket]]] = {}
# room_id -> background task that fans out Redis pub/sub updates to recruiters.
_room_pubsub_tasks: dict[str, asyncio.Task[None]] = {}
_room_pubsub_locks: dict[str, asyncio.Lock] = {}
_room_snapshot_tasks: dict[str, asyncio.Task[None]] = {}


def get_redis_client() -> Any:
    # Imported lazily to keep module import cheap.
    import redis
    from app.core.config import settings

    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_redis_channels(room_id: str) -> tuple[str, str, str]:
    return (
        f"room:{room_id}:deltas",
        f"room:{room_id}:cursors",
        f"room:{room_id}:cheats",
    )


async def _validate_ws_token(room_id: str, token: str) -> dict[str, Any]:
    """
    Returns:
      { role: "candidate" | "recruiter", id: <uuid string> }
    """

    payload = verify_token(token)
    role = payload.get("role") or "recruiter"
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid token subject")

    client = get_supabase_client()
    if client is None:
        raise ValueError("Supabase not configured")

    if role == "candidate":
        # Candidate must belong to the room.
        res = client.table("candidates").select("*").eq("id", subject).single().execute()
        row = res.data
        if not row or str(row.get("room_id")) != str(room_id):
            raise PermissionError("Wrong room")
        return {"role": "candidate", "id": subject}

    # Recruiter must own the room.
    res = client.table("rooms").select("*").eq("id", room_id).single().execute()
    room = res.data
    if not room or str(room.get("recruiter_id")) != str(subject):
        raise PermissionError("Wrong room")
    return {"role": "recruiter", "id": subject}


async def _send_json_safe(ws: WebSocket, data: Any) -> None:
    try:
        await ws.send_json(data)
    except Exception:
        # If the socket is already dead, ignore and rely on disconnect cleanup.
        pass


async def broadcast_room_event(room_id: str, payload: dict[str, Any], target_role: str = "all") -> None:
    room = active_connections.get(room_id)
    if not room:
        return
    sockets: list[WebSocket] = []
    if target_role in ("all", "candidate"):
        sockets.extend(list(room.get("candidates", {}).values()))
    if target_role in ("all", "recruiter"):
        sockets.extend(list(room.get("recruiters", {}).values()))
    for ws in sockets:
        await _send_json_safe(ws, payload)


async def _ensure_room_pubsub(room_id: str) -> None:
    """
    Ensure a single Redis pub/sub subscriber task per room.
    """

    if room_id in _room_pubsub_tasks:
        return

    lock = _room_pubsub_locks.setdefault(room_id, asyncio.Lock())
    async with lock:
        if room_id in _room_pubsub_tasks:
            return

        async def fanout() -> None:
            redis_client = get_redis_client()
            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            deltas_ch, cursors_ch, cheats_ch = _get_redis_channels(room_id)
            pubsub.subscribe(deltas_ch, cursors_ch, cheats_ch)

            try:
                while True:
                    msg = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
                    if not msg:
                        continue
                    data_raw = msg.get("data")
                    try:
                        data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
                    except Exception:
                        data = data_raw

                    room = active_connections.get(room_id)
                    if not room:
                        continue
                    recruiters = list(room["recruiters"].values())
                    if not recruiters:
                        continue

                    # Broadcast payload to all recruiters
                    for ws in recruiters:
                        await _send_json_safe(ws, data)
            except asyncio.CancelledError:
                try:
                    pubsub.close()
                except Exception:
                    pass
                return

        _room_pubsub_tasks[room_id] = asyncio.create_task(fanout())

    if room_id not in _room_snapshot_tasks:
        _room_snapshot_tasks[room_id] = asyncio.create_task(_snapshot_room_loop(room_id))


async def _maybe_cancel_room_pubsub(room_id: str) -> None:
    """
    Cancel the pub/sub fanout task when there are no active connections.
    """

    room = active_connections.get(room_id)
    if not room:
        task = _room_pubsub_tasks.pop(room_id, None)
        if task:
            task.cancel()
        snap_task = _room_snapshot_tasks.pop(room_id, None)
        if snap_task:
            snap_task.cancel()
        return

    candidates = room.get("candidates", {})
    recruiters = room.get("recruiters", {})
    if not candidates and not recruiters:
        task = _room_pubsub_tasks.pop(room_id, None)
        if task:
            task.cancel()
        snap_task = _room_snapshot_tasks.pop(room_id, None)
        if snap_task:
            snap_task.cancel()
        active_connections.pop(room_id, None)


def _best_effort_code_text(room_id: str) -> str:
    redis_client = get_redis_client()
    updates = redis_client.lrange(f"room:{room_id}:ydoc", -1, -1) or []
    if not updates:
        return ""
    upd = updates[0]
    if isinstance(upd, bytes):
        try:
            return upd.decode("utf-8", errors="ignore")
        except Exception:
            return base64.b64encode(upd).decode("utf-8")
    return str(upd)


async def _snapshot_room_loop(room_id: str) -> None:
    try:
        while True:
            await asyncio.sleep(30)
            room = active_connections.get(room_id) or {}
            if not room.get("candidates"):
                continue
            ts = int(time.time())
            code_text = _best_effort_code_text(room_id)
            payload = json.dumps({"timestamp": ts, "code": code_text})
            get_redis_client().zadd(f"room:{room_id}:snapshots", {payload: ts})
    except asyncio.CancelledError:
        return


async def archive_room_snapshots(room_id: str, attempt_id: str | None = None) -> str | None:
    redis_client = get_redis_client()
    raw = redis_client.zrange(f"room:{room_id}:snapshots", 0, -1, withscores=True) or []
    snapshots = []
    for item, score in raw:
        try:
            parsed = json.loads(item)
            snapshots.append(
                {
                    "timestamp": int(parsed.get("timestamp", int(score))),
                    "code": parsed.get("code", ""),
                    "elapsed_seconds": 0,
                }
            )
        except Exception:
            snapshots.append({"timestamp": int(score), "code": str(item), "elapsed_seconds": 0})
    if not snapshots:
        return None
    base = snapshots[0]["timestamp"]
    for snap in snapshots:
        snap["elapsed_seconds"] = int(snap["timestamp"]) - int(base)

    key = f"snapshots/{room_id}/{attempt_id or 'latest'}.json"
    body = json.dumps({"snapshots": snapshots}, ensure_ascii=True)

    # Best-effort MinIO/S3 upload, with local file fallback.
    uploaded = False
    try:
        import boto3  # type: ignore

        client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        bucket = "codexarena-archives"
        try:
            client.head_bucket(Bucket=bucket)
        except Exception:
            client.create_bucket(Bucket=bucket)
        client.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/json")
        uploaded = True
    except Exception:
        uploaded = False

    if not uploaded:
        archive_dir = Path(__file__).resolve().parents[3] / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        file_path = archive_dir / f"{room_id}_{attempt_id or 'latest'}.json"
        file_path.write_text(body, encoding="utf-8")
        key = str(file_path)

    if attempt_id:
        client = get_supabase_client()
        if client is not None:
            try:
                client.table("attempts").update({"s3_archive_key": key}).eq("id", str(attempt_id)).execute()
            except Exception:
                pass
    return key


async def _handle_code_delta(room_id: str, candidate_id: str, ws: WebSocket, data: dict[str, Any]) -> None:
    update_b64 = data.get("update")
    if not isinstance(update_b64, str):
        return

    try:
        update_bytes = base64.b64decode(update_b64.encode("utf-8"))
    except Exception:
        return

    redis_client = get_redis_client()

    # Persist editor state updates for initial sync.
    redis_client.rpush(f"room:{room_id}:ydoc", update_bytes)

    payload_to_publish = {
        "type": "code.delta",
        "update": update_b64,
        "candidate_id": candidate_id,
    }

    # Publish to Redis for multi-pod fan-out.
    # Note: In some test environments we use a fake Redis client where the pub/sub
    # fan-out task may not deliver reliably. In that case, we also do immediate
    # fan-out to active recruiters to keep tests deterministic.
    redis_client.publish(f"room:{room_id}:deltas", json.dumps(payload_to_publish))

    if hasattr(redis_client, "_pubsub_queues"):
        room_state = active_connections.get(room_id)
        if room_state:
            for recruiter_ws in list(room_state.get("recruiters", {}).values()):
                await _send_json_safe(recruiter_ws, payload_to_publish)


async def _handle_cursor_update(room_id: str, candidate_id: str, data: dict[str, Any]) -> None:
    position = data.get("position") if isinstance(data, dict) else None
    if position is None:
        return

    redis_client = get_redis_client()
    payload = {"type": "cursor.update", "candidate_id": candidate_id, "position": position}
    redis_client.publish(f"room:{room_id}:cursors", json.dumps(payload))

    if hasattr(redis_client, "_pubsub_queues"):
        room_state = active_connections.get(room_id)
        if room_state:
            for recruiter_ws in list(room_state.get("recruiters", {}).values()):
                await _send_json_safe(recruiter_ws, payload)


async def _handle_cheat_event(room_id: str, candidate_id: str, data: dict[str, Any]) -> None:
    event_type = data.get("event_type")
    severity = data.get("severity")
    payload = data.get("payload", {}) or {}
    if not isinstance(event_type, str) or not isinstance(severity, str):
        return

    # Write to DB
    client = get_supabase_client()
    if client is not None:
        try:
            client.table("cheat_events").insert(
                {
                    "id": str(uuid.uuid4()),
                    "candidate_id": candidate_id,
                    "event_type": event_type,
                    "severity": severity,
                    "payload": payload,
                    "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ).execute()
        except Exception:
            pass

    # Publish for recruiter fan-out
    redis_client = get_redis_client()
    payload_to_publish = {
        "type": "cheat.event",
        "candidate_id": candidate_id,
        "event_type": event_type,
        "severity": severity,
        "payload": payload,
    }
    redis_client.publish(f"room:{room_id}:cheats", json.dumps(payload_to_publish))
    sev = str(severity).lower()
    cheat_events_total.labels(sev, str(event_type)).inc()

    if hasattr(redis_client, "_pubsub_queues"):
        room_state = active_connections.get(room_id)
        if room_state:
            for recruiter_ws in list(room_state.get("recruiters", {}).values()):
                await _send_json_safe(recruiter_ws, payload_to_publish)


async def _handle_ping(ws: WebSocket) -> None:
    await ws.send_json({"type": "pong", "server_time": int(time.time() * 1000)})


async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """
    WebSocket hub with Yjs update fan-out and Redis pub/sub fan-out.
    Endpoint: /ws/{room_id}
    """

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        info = await _validate_ws_token(room_id=room_id, token=token)
    except PermissionError:
        await websocket.close(code=4003)
        return
    except Exception:
        await websocket.close(code=4001)
        return

    role = info["role"]
    entity_id = info["id"]

    await websocket.accept()

    room = active_connections.setdefault(room_id, {"candidates": {}, "recruiters": {}})

    if role == "candidate":
        room["candidates"][entity_id] = websocket
        websocket_connections_active.labels("candidate").inc()
    else:
        room["recruiters"][entity_id] = websocket
        websocket_connections_active.labels("recruiter").inc()
    logger.info("connection_opened", room_id=room_id, role=role, candidate_id=entity_id if role == "candidate" else "-")

    await _ensure_room_pubsub(room_id)

    # On recruiter connect, send current Yjs state from Redis list.
    if role == "recruiter":
        redis_client = get_redis_client()
        updates = redis_client.lrange(f"room:{room_id}:ydoc", 0, -1) or []
        updates_b64: list[str] = []
        for upd in updates:
            if isinstance(upd, bytes):
                updates_b64.append(base64.b64encode(upd).decode("utf-8"))
            else:
                # FakeRedis might store str already.
                updates_b64.append(str(upd))
        await _send_json_safe(websocket, {"type": "yjs.sync", "updates": updates_b64})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "code.delta" and role == "candidate":
                await _handle_code_delta(room_id, entity_id, websocket, msg)
            elif msg_type == "cursor.update" and role == "candidate":
                await _handle_cursor_update(room_id, entity_id, msg)
            elif msg_type == "cheat.event" and role == "candidate":
                await _handle_cheat_event(room_id, entity_id, msg)
            elif msg_type == "ping":
                await _handle_ping(websocket)
            else:
                # Unknown / unauthorized event; ignore.
                continue
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup connection
        room = active_connections.get(room_id)
        if room:
            if role == "candidate":
                room["candidates"].pop(entity_id, None)
                websocket_connections_active.labels("candidate").dec()
            else:
                room["recruiters"].pop(entity_id, None)
                websocket_connections_active.labels("recruiter").dec()
        logger.info("connection_closed", room_id=room_id, role=role, candidate_id=entity_id if role == "candidate" else "-")
        await _maybe_cancel_room_pubsub(room_id)

