from __future__ import annotations

import base64
import json
import time
import sys
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Optional
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import supabase

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.api.routes import candidates as candidates_routes
from app.api.routes import rooms as rooms_routes
from app.services.realtime import websocket_hub


class FakePubSub:
    def __init__(self, redis: "FakeRedis", ignore_subscribe_messages: bool = True):
        self._redis = redis
        self._ignore = ignore_subscribe_messages
        self._channels: set[str] = set()

    def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self._channels.add(ch)

    def close(self) -> None:
        # no-op for fake
        return None

    def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 0.1) -> Optional[dict[str, Any]]:
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            for ch in list(self._channels):
                q = self._redis._pubsub_queues.get(ch)
                if q and len(q) > 0:
                    msg = q.popleft()
                    return msg
            time.sleep(0.005)
        return None


class FakeRedis:
    def __init__(self):
        self._kv: dict[str, Any] = {}
        self._kv_exp: dict[str, float] = {}
        self._lists: dict[str, list[Any]] = {}
        self._counters: dict[str, int] = {}
        self._pubsub_queues: dict[str, Deque[dict[str, Any]]] = {}

    def _cleanup(self, key: str) -> None:
        exp = self._kv_exp.get(key)
        if exp is not None and time.time() >= exp:
            self._kv.pop(key, None)
            self._kv_exp.pop(key, None)
            self._counters.pop(key, None)

    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, **kwargs: Any) -> bool:
        self._cleanup(key)
        if nx and key in self._kv:
            return False
        self._kv[key] = value
        if ex is not None:
            self._kv_exp[key] = time.time() + float(ex)
        return True

    def get(self, key: str) -> Any:
        self._cleanup(key)
        return self._kv.get(key)

    def delete(self, key: str) -> int:
        self._cleanup(key)
        existed = 1 if key in self._kv else 0
        self._kv.pop(key, None)
        self._kv_exp.pop(key, None)
        self._counters.pop(key, None)
        return existed

    def incr(self, key: str) -> int:
        self._cleanup(key)
        self._counters[key] = self._counters.get(key, 0) + 1
        # also mirror into kv for get() semantics in some flows
        self._kv[key] = self._counters[key]
        return self._counters[key]

    def expire(self, key: str, ex: int) -> bool:
        self._kv_exp[key] = time.time() + float(ex)
        return True

    def rpush(self, key: str, value: Any) -> int:
        self._lists.setdefault(key, [])
        self._lists[key].append(value)
        return len(self._lists[key])

    def lrange(self, key: str, start: int, end: int) -> list[Any]:
        items = self._lists.get(key, [])
        if end == -1:
            end = len(items) - 1
        return items[start : end + 1]

    def publish(self, channel: str, message: str) -> int:
        q = self._pubsub_queues.setdefault(channel, deque())
        q.append({"type": "message", "channel": channel, "data": message})
        return 1

    def pubsub(self, ignore_subscribe_messages: bool = True) -> FakePubSub:
        return FakePubSub(self, ignore_subscribe_messages=ignore_subscribe_messages)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    supabase.reset_db()
    fake_redis = FakeRedis()

    # Patch all redis access points used by websocket flow.
    monkeypatch.setattr(websocket_hub, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(rooms_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(candidates_routes, "get_redis_client", lambda: fake_redis)

    return TestClient(app)


def _create_recruiter_token(client: TestClient) -> str:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    reg = client.post("/auth/register", json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"})
    assert reg.status_code == 200

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_room_and_candidate(client: TestClient, recruiter_token: str) -> tuple[str, str, str]:
    created = client.post(
        "/rooms",
        json={"title": "Senior Python", "difficulty": "medium"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert created.status_code == 200
    room_id = created.json()["room_id"]
    join_token = created.json()["join_link"].split("/")[-1]

    joined = client.post(f"/rooms/{room_id}/join", json={"name": "Alice", "join_token": join_token})
    assert joined.status_code == 200
    candidate_id = joined.json()["candidate_id"]
    candidate_token = joined.json()["candidate_token"]
    return room_id, candidate_id, candidate_token


def test_websocket_connect_invalid_token_closes_4001(client: TestClient) -> None:
    # Create a room so room_id is valid.
    recruiter_token = _create_recruiter_token(client)
    room_id, _candidate_id, _candidate_token = _create_room_and_candidate(client, recruiter_token)

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/ws/{room_id}") as ws:
            ws.receive_text()

    assert excinfo.value.code == 4001


def test_websocket_wrong_room_closes_4003(client: TestClient) -> None:
    recruiter_token = _create_recruiter_token(client)

    room1_id, _candidate1_id, candidate1_token = _create_room_and_candidate(client, recruiter_token)
    room2_id, _candidate2_id, _candidate2_token = _create_room_and_candidate(client, recruiter_token)

    # Candidate token from room1 tries to connect to room2.
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/ws/{room2_id}?token={candidate1_token}") as ws:
            ws.receive_text()

    assert excinfo.value.code == 4003


def test_websocket_code_delta_fanout_and_ydoc_sync(client: TestClient) -> None:
    recruiter_token = _create_recruiter_token(client)
    room_id, _candidate_id, candidate_token = _create_room_and_candidate(client, recruiter_token)

    with client.websocket_connect(f"/ws/{room_id}?token={candidate_token}") as candidate_ws:
        with client.websocket_connect(f"/ws/{room_id}?token={recruiter_token}") as recruiter_ws:
            sync_msg = recruiter_ws.receive_json()
            assert sync_msg["type"] == "yjs.sync"

            # Send one yjs update.
            update_bytes = b"hello-yjs"
            update_b64 = base64.b64encode(update_bytes).decode("utf-8")

            t0 = time.monotonic()
            candidate_ws.send_json({"type": "code.delta", "update": update_b64})

            # Recruiter should receive the broadcast quickly.
            received = recruiter_ws.receive_json()
            elapsed = time.monotonic() - t0
            assert elapsed < 0.5
            assert received["type"] == "code.delta"
            assert received["update"] == update_b64

        # Disconnect recruiter then reconnect; it should receive full ydoc sync.
        with client.websocket_connect(f"/ws/{room_id}?token={recruiter_token}") as recruiter_ws2:
            sync2 = recruiter_ws2.receive_json()
            assert sync2["type"] == "yjs.sync"
            assert update_b64 in sync2["updates"]

