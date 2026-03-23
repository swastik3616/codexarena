from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import supabase

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.api.routes import rooms as rooms_routes
from app.api.routes import candidates as candidates_routes
from app.services.execution import runner as runner_module
from app.db.database import get_supabase_client


class FakeRedis:
    def __init__(self):
        self._kv: dict[str, Any] = {}
        self._exp: dict[str, float] = {}
        self._count: dict[str, int] = {}

    def _cleanup(self, key: str) -> None:
        exp = self._exp.get(key)
        if exp is not None and time.time() >= exp:
            self._kv.pop(key, None)
            self._exp.pop(key, None)
            self._count.pop(key, None)

    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, **kwargs: Any) -> bool:
        self._cleanup(key)
        if nx and key in self._kv:
            return False
        self._kv[key] = value
        if ex is not None:
            self._exp[key] = time.time() + float(ex)
        return True

    def get(self, key: str) -> Any:
        self._cleanup(key)
        return self._kv.get(key)

    def delete(self, key: str) -> int:
        self._cleanup(key)
        existed = 1 if key in self._kv else 0
        self._kv.pop(key, None)
        self._exp.pop(key, None)
        self._count.pop(key, None)
        return existed

    def incr(self, key: str) -> int:
        self._cleanup(key)
        self._count[key] = self._count.get(key, 0) + 1
        self._kv[key] = self._count[key]
        return self._count[key]

    def expire(self, key: str, ex: int) -> bool:
        self._exp[key] = time.time() + float(ex)
        return True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    supabase.reset_db()
    fake_redis = FakeRedis()
    monkeypatch.setattr(rooms_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(candidates_routes, "get_redis_client", lambda: fake_redis)

    async def fake_execute_code(*, code: str, language: str, test_cases: list[dict]) -> dict[str, Any]:
        # Pretend all generated test cases pass internal sandbox validation.
        return {
            "attempt_id": "qgen",
            "pass_count": len(test_cases),
            "total": len(test_cases),
            "results": [{"id": tc.get("id"), "passed": True, "actual": tc.get("expected"), "time_ms": 0} for tc in test_cases],
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
            "wall_time_ms": 1,
            "timed_out": False,
        }

    monkeypatch.setattr(runner_module, "execute_code", fake_execute_code)
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, password: str = "TestPass123!") -> str:
    reg = client.post("/auth/register", json={"email": email, "password": password, "name": "Recruiter", "company": "Acme"})
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_candidate_token(client: TestClient, recruiter_token: str) -> str:
    created = client.post("/rooms", json={"title": "QGen Room", "difficulty": "medium"}, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert created.status_code == 200
    room_id = created.json()["room_id"]
    join_token = created.json()["join_link"].split("/")[-1]
    joined = client.post(f"/rooms/{room_id}/join", json={"name": "Candidate A", "join_token": join_token})
    assert joined.status_code == 200
    return joined.json()["candidate_token"]


def test_question_generate_and_visibility(client: TestClient) -> None:
    recruiter_token = _register_and_login(client, email=f"r-{uuid4()}@example.com")
    candidate_token = _create_candidate_token(client, recruiter_token)

    # 1) POST /questions/generate
    gen = client.post(
        "/questions/generate",
        json={"difficulty": "medium", "topic_tags": ["arrays", "hash-map"], "language": "python"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert gen.status_code == 200
    body = gen.json()
    assert body["question_id"]
    qid = body["question_id"]

    # 2) Exactly 8 test cases in DB
    supa = get_supabase_client()
    assert supa is not None
    qrow = supa.table("questions").select("*").eq("id", qid).single().execute().data
    assert qrow is not None
    assert len(qrow.get("test_cases", [])) == 8

    # 3) validation_status = validated
    assert qrow.get("validation_status") == "validated"

    # 4) Candidate view strips expected_output
    cand_get = client.get(f"/questions/{qid}", headers={"Authorization": f"Bearer {candidate_token}"})
    assert cand_get.status_code == 200
    for tc in cand_get.json().get("test_cases", []):
        assert "expected_output" not in tc

    # 5) Recruiter view includes expected_output
    rec_get = client.get(f"/questions/{qid}", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert rec_get.status_code == 200
    for tc in rec_get.json().get("test_cases", []):
        assert "expected_output" in tc

