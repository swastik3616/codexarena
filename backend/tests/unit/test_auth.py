from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
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
from jose import jwt

import supabase
from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.main import app


class FakeRedis:
    def __init__(self):
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any, nx: bool = False, ex: Optional[int] = None) -> bool:
        # TTL is ignored for unit tests; single-use behavior is validated by key existence.
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    supabase.reset_db()
    fake_redis = FakeRedis()
    monkeypatch.setattr(auth_routes, "get_redis_client", lambda: fake_redis)
    return TestClient(app)


def _register(client: TestClient, *, email: str, password: str) -> dict[str, Any]:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    return resp.json()


def test_register_success(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "recruiter" in data
    assert data["recruiter"]["email"] == email


def test_login_success(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    r1 = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert r1.status_code == 200

    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["recruiter"]["email"] == email


def test_login_wrong_password(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    r1 = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert r1.status_code == 200

    resp = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert resp.status_code == 401


def test_expired_token(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert resp.status_code == 200
    recruiter_id = resp.json()["recruiter"]["id"]

    expired_payload = {
        "sub": recruiter_id,
        "email": email,
        "jti": str(uuid4()),
        "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
    }
    expired_access_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    me = client.get("/auth/protected", headers={"Authorization": f"Bearer {expired_access_token}"})
    assert me.status_code == 401


def test_refresh_token(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    reg = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert reg.status_code == 200

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != old_refresh


def test_refresh_token_reuse(client: TestClient) -> None:
    email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"

    reg = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"},
    )
    assert reg.status_code == 200

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    resp1 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp1.status_code == 200

    resp2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp2.status_code == 401

