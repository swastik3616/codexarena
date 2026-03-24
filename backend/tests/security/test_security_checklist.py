from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
import supabase

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.api.routes import auth as auth_routes
from app.api.routes import rooms as rooms_routes
from app.api.routes import candidates as candidates_routes
from app.api.routes import questions as questions_routes
from app.core.security import create_access_token
from app.db.database import get_supabase_client


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.counts = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None, nx=False, **kwargs):
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    def delete(self, key):
        existed = 1 if key in self.kv else 0
        self.kv.pop(key, None)
        return existed

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        self.kv[key] = self.counts[key]
        return self.counts[key]

    def expire(self, key, ex):
        return True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    supabase.reset_db()
    r = FakeRedis()
    monkeypatch.setattr(auth_routes, "get_redis_client", lambda: r)
    monkeypatch.setattr(rooms_routes, "get_redis_client", lambda: r)
    monkeypatch.setattr(candidates_routes, "get_redis_client", lambda: r)
    monkeypatch.setattr(questions_routes, "get_redis_client", lambda: r)
    async def _fake_generate(self, difficulty: str, topic_tags: list, language: str):
        return {
            "id": str(uuid4()),
            "title": "Stub",
            "description": "Stub question",
            "difficulty": difficulty,
            "topic_tags": topic_tags or [],
            "hints": [],
            "examples": [],
        }
    monkeypatch.setattr(candidates_routes.QuestionGenerator, "generate", _fake_generate)
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, password: str = "TestPass123!"):
    reg = client.post("/auth/register", json={"email": email, "password": password, "name": "R", "company": "C"})
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_cors_blocks_unknown_origin(client: TestClient):
    res = client.options("/health", headers={"Origin": "https://unknown.example", "Access-Control-Request-Method": "GET"})
    assert res.headers.get("access-control-allow-origin") is None


def test_jwt_tampered(client: TestClient):
    token = create_access_token({"sub": "x", "email": "x@x.com", "jti": "j1"})
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert res.status_code == 401


def test_sql_injection(client: TestClient):
    token = _register_and_login(client, f"{uuid4()}@example.com")
    created = client.post("/rooms", json={"title": "Room", "difficulty": "medium"}, headers={"Authorization": f"Bearer {token}"})
    room_id = created.json()["room_id"]
    join_token = created.json()["join_link"].split("/")[-1]
    payload = {"name": "'; DROP TABLE candidates; --", "join_token": join_token}
    joined = client.post(f"/rooms/{room_id}/join", json=payload)
    assert joined.status_code == 200
    cid = joined.json()["candidate_id"]
    row = get_supabase_client().table("candidates").select("*").eq("id", cid).single().execute().data
    assert row["name"] == payload["name"]


def test_xss_input(client: TestClient):
    token = _register_and_login(client, f"{uuid4()}@example.com")
    title = "<script>alert(1)</script>"
    created = client.post("/rooms", json={"title": title, "difficulty": "medium"}, headers={"Authorization": f"Bearer {token}"})
    assert created.status_code == 200
    room_id = created.json()["room_id"]
    detail = client.get(f"/rooms/{room_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail.status_code == 200
    assert detail.json()["room"]["title"] == title


def test_rate_limit_login(client: TestClient):
    _register_and_login(client, f"{uuid4()}@example.com")
    email = f"{uuid4()}@example.com"
    client.post("/auth/register", json={"email": email, "password": "TestPass123!", "name": "R", "company": "C"})
    for _ in range(10):
        client.post("/auth/login", json={"email": email, "password": "wrong"})
    res = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert res.status_code == 429


def test_auth_required(client: TestClient):
    assert client.post("/rooms", json={"title": "x", "difficulty": "easy"}).status_code == 401


def test_room_ownership(client: TestClient):
    token_a = _register_and_login(client, f"a-{uuid4()}@example.com")
    token_b = _register_and_login(client, f"b-{uuid4()}@example.com")
    created = client.post("/rooms", json={"title": "Private", "difficulty": "medium"}, headers={"Authorization": f"Bearer {token_a}"})
    room_id = created.json()["room_id"]
    detail = client.get(f"/rooms/{room_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert detail.status_code == 403

