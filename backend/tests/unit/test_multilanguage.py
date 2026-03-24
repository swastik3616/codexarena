from __future__ import annotations

import io
import asyncio
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[2]
import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.execution import runner


class FakeContainer:
    def __init__(self, language: str):
        self.language = language
        self.files: dict[str, bytes] = {}

    def put_archive(self, target: str, data: bytes) -> bool:
        bio = io.BytesIO(data)
        with tarfile.open(fileobj=bio, mode="r") as tar:
            for m in tar.getmembers():
                if m.isfile():
                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    path = "/" + m.name.lstrip("/")
                    self.files[path] = f.read()
        return True

    def exec_run(self, cmd: str, demux: bool = True):
        test_cases_raw = self.files.get("/tmp/test_cases.json", b"[]").decode("utf-8")
        test_cases = json.loads(test_cases_raw)

        # Pick whichever source file exists for this fake language.
        candidates = [
            "/tmp/submission/solution.py",
            "/tmp/submission/solution.js",
            "/tmp/submission/Solution.java",
            "/tmp/submission/solution.cpp",
            "/tmp/submission/solution.go",
        ]
        code = ""
        for p in candidates:
            if p in self.files:
                code = self.files[p].decode("utf-8", errors="replace")
                break

        if "__RUNTIME_ERROR__" in code:
            return (1, (b"", b"RuntimeError: boom"))

        results = []
        wrong = "__WRONG__" in code
        for i, tc in enumerate(test_cases):
            expected = str(tc.get("expected_output", tc.get("expected", "")))
            passed = not wrong
            results.append(
                {
                    "id": tc.get("id", i + 1),
                    "passed": passed,
                    "actual": "0" if wrong else expected,
                    "expected": expected,
                    "time_ms": 1,
                }
            )
        stdout = json.dumps({"results": results}).encode("utf-8")
        return (0, (stdout, b""))

    def kill(self):
        return None

    def stop(self):
        return None


class FakePool:
    def __init__(self, language: str):
        self.container = FakeContainer(language)

    async def start(self):
        return None

    async def get_idle(self):
        return self.container

    async def release(self, container):
        return None

    async def recycle_on_timeout(self, container):
        return None


LANGUAGES = ["python", "javascript", "java", "cpp", "go"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_correct_solution_all_pass(monkeypatch: pytest.MonkeyPatch, language: str):
    async def fake_get_pool(lang: str):
        return FakePool(lang)

    monkeypatch.setattr(runner, "_get_pool", fake_get_pool)

    code = "// CORRECT\nprint(1)\n"
    test_cases = [
        {"id": 1, "input": "a\n", "expected_output": "4"},
        {"id": 2, "input": "b\n", "expected_output": "5"},
    ]
    res = asyncio.run(runner.execute_code(code=code, language=language, test_cases=test_cases))
    assert res["pass_count"] == res["total"] == 2
    assert all(r["passed"] for r in res["results"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_wrong_solution_reports_failures(monkeypatch: pytest.MonkeyPatch, language: str):
    async def fake_get_pool(lang: str):
        return FakePool(lang)

    monkeypatch.setattr(runner, "_get_pool", fake_get_pool)

    code = "// __WRONG__\n"
    test_cases = [
        {"id": 1, "input": "a\n", "expected_output": "4"},
        {"id": 2, "input": "b\n", "expected_output": "5"},
    ]
    res = asyncio.run(runner.execute_code(code=code, language=language, test_cases=test_cases))
    assert res["pass_count"] < res["total"]
    assert any(not r["passed"] for r in res["results"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_runtime_error_captured(monkeypatch: pytest.MonkeyPatch, language: str):
    async def fake_get_pool(lang: str):
        return FakePool(lang)

    monkeypatch.setattr(runner, "_get_pool", fake_get_pool)

    code = "// __RUNTIME_ERROR__\n"
    test_cases = [{"id": 1, "input": "", "expected_output": "x"}]
    res = asyncio.run(runner.execute_code(code=code, language=language, test_cases=test_cases))
    assert res["timed_out"] is False
    assert "RuntimeError" in (res.get("stderr") or "") or res["pass_count"] == 0

