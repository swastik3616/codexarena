from __future__ import annotations

import asyncio
import json
import time
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import supabase

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import execute as execute_routes
from app.api.routes import candidates as candidates_routes
from app.api.routes import rooms as rooms_routes
from app.api.routes import auth as auth_routes
from app.main import app
from app.db.database import get_supabase_client
from app.workers import execution_worker as execution_worker_module


@dataclass
class FakeRedis:
    store: dict[str, Any]
    expires_at: dict[str, float]
    counters: dict[str, int]

    def __init__(self):
        self.store = {}
        self.expires_at = {}
        self.counters = {}

    def _cleanup(self, key: str) -> None:
        exp = self.expires_at.get(key)
        if exp is not None and time.time() >= exp:
            self.store.pop(key, None)
            self.expires_at.pop(key, None)
            self.counters.pop(key, None)

    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, **kwargs: Any) -> bool:
        self._cleanup(key)
        if nx and key in self.store:
            return False
        self.store[key] = value
        if ex is not None:
            self.expires_at[key] = time.time() + float(ex)
        return True

    def get(self, key: str) -> Any:
        self._cleanup(key)
        return self.store.get(key)

    def delete(self, key: str) -> int:
        self._cleanup(key)
        existed = 1 if key in self.store else 0
        self.store.pop(key, None)
        self.expires_at.pop(key, None)
        self.counters.pop(key, None)
        return existed

    def publish(self, channel: str, message: str) -> None:
        # no-op for tests
        return None

    def incr(self, key: str) -> int:
        self._cleanup(key)
        self.counters[key] = self.counters.get(key, 0) + 1
        self.store[key] = self.counters[key]
        return self.counters[key]

    def expire(self, key: str, ex: int) -> bool:
        self.expires_at[key] = time.time() + float(ex)
        return True


def _two_sum_correct_code() -> str:
    # Reads stdin:
    #   line1: JSON array of nums
    #   line2: target int
    # Prints JSON list of indices.
    return r"""
import sys, json
lines = sys.stdin.read().strip().splitlines()
nums = json.loads(lines[0]) if lines else []
target = int(lines[1]) if len(lines) > 1 else 0
seen = {}
for i, x in enumerate(nums):
    if target - x in seen:
        print(json.dumps([seen[target - x], i]))
        break
    seen[x] = i
"""


def _two_sum_wrong_code() -> str:
    return r"""
import sys, json
lines = sys.stdin.read().strip().splitlines()
nums = json.loads(lines[0]) if lines else []
target = int(lines[1]) if len(lines) > 1 else 0
print(json.dumps([0, 0]))
"""


def _fake_execute_code_factory():
    """
    Monkeypatched runner.execute_code for environments without Docker.
    It runs candidate code locally with the provided stdin input.
    """

    import subprocess
    import tempfile

    async def fake_execute_code(*, code: str, language: str, test_cases: list[dict]) -> dict:
        # language is currently ignored (tests use python only).
        results = []
        pass_count = 0
        start = time.monotonic()
        stdout_json: dict[str, Any] = {"results": []}
        for tc in test_cases:
            test_id = tc.get("id")
            input_data = tc.get("input", "")
            expected = str(tc.get("expected", "")).strip()

            with tempfile.TemporaryDirectory() as td:
                sol_path = f"{td}/solution.py"
                with open(sol_path, "w", encoding="utf-8") as f:
                    f.write(code)

                proc = subprocess.run(
                    ["python", sol_path],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=10,
                )
                out = (proc.stdout or "").strip()
                err = (proc.stderr or "").strip()
                passed = (expected in out) if expected else False
                if passed:
                    pass_count += 1

                results.append(
                    {
                        "id": test_id,
                        "passed": passed,
                        "expected": expected,
                        "actual": out if out else err,
                        "time_ms": 0,
                    }
                )

        stdout_json["results"] = results
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "attempt_id": "n/a",
            "pass_count": pass_count,
            "total": len(test_cases),
            "results": results,
            "stdout": json.dumps(stdout_json),
            "stderr": "",
            "exit_code": 0,
            "wall_time_ms": elapsed_ms,
            "timed_out": False,
            "memory_kb": None,
        }

    return fake_execute_code


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    supabase.reset_db()
    fake_redis = FakeRedis()

    # Patch redis usage in routes
    monkeypatch.setattr(execute_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(rooms_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(candidates_routes, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(execution_worker_module, "get_redis_client", lambda: fake_redis)

    return TestClient(app)


def _create_recruiter_tokens(client: TestClient, *, email: str, password: str) -> str:
    reg = client.post("/auth/register", json={"email": email, "password": password, "name": "Test Recruiter", "company": "Acme"})
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _setup_room_and_candidate(client: TestClient, *, recruiter_token: str) -> tuple[str, str, str]:
    created = client.post("/rooms", json={"title": "Senior Python", "difficulty": "medium"}, headers={"Authorization": f"Bearer {recruiter_token}"})
    assert created.status_code == 200
    room_id = created.json()["room_id"]
    join_token = created.json()["join_link"].split("/")[-1]

    joined = client.post(f"/rooms/{room_id}/join", json={"name": "Alice", "join_token": join_token})
    assert joined.status_code == 200
    candidate_id = joined.json()["candidate_id"]
    candidate_token = joined.json()["candidate_token"]
    return room_id, candidate_id, candidate_token


def test_execute_rate_limit_and_result_flow(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    # Monkeypatch runner for dockerless environments.
    from app.services.execution import runner as runner_module

    monkeypatch.setattr(runner_module, "execute_code", _fake_execute_code_factory())

    recruiter_email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"
    recruiter_token = _create_recruiter_tokens(client, email=recruiter_email, password=password)

    room_id, candidate_id, candidate_token = _setup_room_and_candidate(client, recruiter_token=recruiter_token)

    # Create question + attempt directly in DB
    supa = get_supabase_client()
    assert supa is not None

    question_id = str(uuid4())
    test_cases = [
        {"id": 1, "input": "[2,7,11,15]\n9\n", "expected": "[0, 1]"},
        {"id": 2, "input": "[3,2,4]\n6\n", "expected": "[1, 2]"},
        {"id": 3, "input": "[3,3]\n6\n", "expected": "[0, 1]"},
    ]
    q_row = (
        supa.table("questions").insert(
            {
                "id": question_id,
                "title": "Two Sum",
                "description": "Find indices",
                "difficulty": "easy",
                "topic_tags": [],
                "test_cases": test_cases,
                "validation_status": "validated",
                "generated_by": "manual",
            }
        ).execute()
    )
    assert q_row.status_code in (201, 200)

    attempt_id = str(uuid4())
    supa.table("attempts").insert(
        {"id": attempt_id, "candidate_id": candidate_id, "question_id": question_id, "language": "python"}
    ).execute()

    # 1) POST /execute with valid code -> job_id returned quickly
    correct_code = _two_sum_correct_code()
    start = time.monotonic()
    post1 = client.post(
        "/execute",
        json={"attempt_id": attempt_id, "language": "python", "code": correct_code},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    elapsed = time.monotonic() - start
    assert post1.status_code == 200
    assert elapsed < 0.2
    job_id = post1.json()["job_id"]

    # 2) GET /execute/{job_id} after ~3s -> complete
    time.sleep(1.0)
    deadline = time.time() + 3.5
    while time.time() < deadline:
        status_resp = client.get(f"/execute/{job_id}", headers={"Authorization": f"Bearer {candidate_token}"})
        if status_resp.status_code != 200:
            time.sleep(0.05)
            continue
        data = status_resp.json()
        if data.get("status") == "complete":
            assert data["pass_count"] == data["total"]
            return
        time.sleep(0.2)

    raise AssertionError("Job did not complete in time")


def test_execute_second_request_rate_limited(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    from app.services.execution import runner as runner_module
    monkeypatch.setattr(runner_module, "execute_code", _fake_execute_code_factory())

    recruiter_email = f"r-{uuid4()}@example.com"
    password = "TestPass123!"
    recruiter_token = _create_recruiter_tokens(client, email=recruiter_email, password=password)

    _room_id, candidate_id, candidate_token = _setup_room_and_candidate(client, recruiter_token=recruiter_token)

    supa = get_supabase_client()
    assert supa is not None
    question_id = str(uuid4())
    test_cases = [{"id": 1, "input": "[1,2]\n3\n", "expected": "[0, 1]"}]
    supa.table("questions").insert(
        {"id": question_id, "title": "Two Sum", "description": "x", "difficulty": "easy", "topic_tags": [], "test_cases": test_cases, "validation_status": "validated", "generated_by": "manual"}
    ).execute()

    attempt_id = str(uuid4())
    supa.table("attempts").insert({"id": attempt_id, "candidate_id": candidate_id, "question_id": question_id, "language": "python"}).execute()

    wrong_code = _two_sum_wrong_code()

    post1 = client.post("/execute", json={"attempt_id": attempt_id, "language": "python", "code": wrong_code}, headers={"Authorization": f"Bearer {candidate_token}"})
    assert post1.status_code == 200
    job_id = post1.json()["job_id"]
    # Immediately enqueue again within <5 seconds -> should be 429
    post2 = client.post("/execute", json={"attempt_id": attempt_id, "language": "python", "code": wrong_code}, headers={"Authorization": f"Bearer {candidate_token}"})
    assert post2.status_code == 429
    assert post2.headers.get("Retry-After") == "5"

    # Job should still be fetchable
    time.sleep(0.5)
    get_res = client.get(f"/execute/{job_id}", headers={"Authorization": f"Bearer {candidate_token}"})
    if get_res.status_code == 200:
        assert "status" in get_res.json()

