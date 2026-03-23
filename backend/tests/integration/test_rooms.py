from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from pathlib import Path

# Ensure `backend/` is on sys.path so `import app...` works when pytest is run
# from the monorepo root.
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

import supabase

from app.api.routes import candidates as candidates_routes
from app.api.routes import rooms as rooms_routes
from app.main import app


@dataclass
class FakeRedis:
    store: dict[str, Any]
    counters: dict[str, int]

    def __init__(self):
        self.store = {}
        self.counters = {}

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self.store[key] = value
        return True

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def delete(self, key: str) -> int:
        existed = 1 if key in self.store else 0
        self.store.pop(key, None)
        return existed

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, ex: int) -> bool:
        # TTL is ignored in unit/integration tests with this fake.
        return True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    supabase.reset_db()
    fake_redis = FakeRedis()

    monkeypatch.setattr(rooms_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(candidates_routes, "get_redis_client", lambda: fake_redis)
    return TestClient(app)


def _register_and_login(client: TestClient, *, email: str, password: str) -> str:
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert reg.status_code == 200

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_room_create_and_single_use_join_and_ownership(client: TestClient) -> None:
    recruiter1_email = f"r1-{uuid4()}@example.com"
    recruiter2_email = f"r2-{uuid4()}@example.com"
    password = "TestPass123!"

    recruiter1_token = _register_and_login(client, email=recruiter1_email, password=password)
    recruiter2_token = _register_and_login(client, email=recruiter2_email, password=password)

    # 1. POST /rooms -> 200 and join_link returned
    created = client.post(
        "/rooms",
        json={"title": "Senior Python", "difficulty": "medium"},
        headers={"Authorization": f"Bearer {recruiter1_token}"},
    )
    assert created.status_code == 200

    body = created.json()
    room_id = body["room_id"]
    join_link = body["join_link"]
    status = body["status"]
    assert status == "pending"
    assert join_link.startswith("https://app.codexarena.io/join/")

    token = join_link.split("/")[-1]

    # 2. POST /rooms/{id}/join with token -> 200 candidate_token returned
    joined = client.post(
        f"/rooms/{room_id}/join",
        json={"name": "Alice", "join_token": token},
    )
    assert joined.status_code == 200
    joined_body = joined.json()
    assert joined_body["candidate_id"]
    assert joined_body["candidate_token"]

    # 3. Reuse same token -> 410 Gone
    joined_again = client.post(
        f"/rooms/{room_id}/join",
        json={"name": "Alice2", "join_token": token},
    )
    assert joined_again.status_code == 410

    # 4. GET /rooms/{id} as different recruiter -> 403
    detail = client.get(
        f"/rooms/{room_id}",
        headers={"Authorization": f"Bearer {recruiter2_token}"},
    )
    assert detail.status_code == 403

