from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

from app.db.database import get_supabase_client

from .pool import LANGUAGE_IMAGES, LANGUAGE_POOLS


def _python_file_ext() -> str:
    return "py"


def _language_to_ext(language: str) -> str:
    return {
        "python": _python_file_ext(),
        "javascript": "js",
        "java": "java",
        "cpp": "cpp",
        "go": "go",
    }[language]


def _solution_filename(language: str) -> str:
    return {
        "python": "solution.py",
        "javascript": "solution.js",
        "java": "Solution.java",
        "cpp": "solution.cpp",
        "go": "solution.go",
    }[language]


def _language_to_runner_name(language: str) -> str:
    return {
        "python": "python_runner.sh",
        "javascript": "js_runner.sh",
        "java": "java_runner.sh",
        "cpp": "cpp_runner.sh",
        "go": "go_runner.sh",
    }[language]


async def _get_pool(language: str):
    pool = LANGUAGE_POOLS.get(language)
    if pool is None:
        raise ValueError(f"Unsupported language: {language}")
    await pool.start()
    return pool


def _write_file_tar_bytes(path_in_container: str, content: bytes) -> bytes:
    """
    Build a minimal tar archive in-memory for docker put_archive.
    """
    import io
    import tarfile

    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w") as tar:
        # Docker's put_archive extracts members relative to the target directory.
        # We will always call put_archive with target='/' so the member path should
        # be absolute-like (sans leading slash).
        info = tarfile.TarInfo(name=path_in_container.lstrip("/"))
        info.size = len(content)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(content))
    bio.seek(0)
    return bio.read()


async def execute_code(code: str, language: str, test_cases: list[dict]) -> dict:
    """
    Execute code inside a warm, security-constrained container pool.
    """

    if language not in LANGUAGE_IMAGES:
        raise ValueError(f"Unsupported language: {language}")

    pool = await _get_pool(language)
    container = await pool.get_idle()

    attempt_id = str(uuid.uuid4())
    # Prepare files in /tmp/submission
    solution_path = f"/tmp/submission/{_solution_filename(language)}"
    test_cases_path = "/tmp/test_cases.json"
    runner_path = "/tmp/runner.sh"

    start = time.monotonic()
    timed_out = False

    try:
        # Ensure directories exist
        await asyncio.to_thread(container.exec_run, "sh -c 'mkdir -p /tmp/submission'")

        # Put solution
        tar_solution = _write_file_tar_bytes(solution_path, code.encode("utf-8"))
        await asyncio.to_thread(container.put_archive, "/", tar_solution)

        # Put test cases
        tar_tests = _write_file_tar_bytes(test_cases_path, json.dumps(test_cases).encode("utf-8"))
        await asyncio.to_thread(container.put_archive, "/", tar_tests)

        # Put runner script
        from pathlib import Path

        runner_file = Path(__file__).resolve().parent / "runners" / _language_to_runner_name(language)
        runner_script = runner_file.read_bytes()
        tar_runner = _write_file_tar_bytes(runner_path, runner_script)
        await asyncio.to_thread(container.put_archive, "/", tar_runner)

        # Run
        def _run():
            # NOTE: container.exec_run is blocking, so we call it in a thread.
            return container.exec_run("sh -c 'chmod +x /tmp/runner.sh && /tmp/runner.sh'", demux=True)

        exec_result = await asyncio.wait_for(asyncio.to_thread(_run), timeout=10)

        # docker SDK returns (exit_code, (stdout, stderr)) for demux=True
        exit_code, output = exec_result
        stdout, stderr = output if output else (b"", b"")
        stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

        # Parse JSON test results if runner produced them.
        parsed: Dict[str, Any] | None = None
        try:
            parsed = json.loads(stdout_text.strip() or "{}")
        except Exception:
            parsed = None

        wall_time_ms = int((time.monotonic() - start) * 1000)

        if not parsed or "results" not in parsed:
            # Runner didn't produce expected JSON: return safe failure shape.
            total = len(test_cases)
            results_out = [
                {
                    "test_id": i,
                    "passed": False,
                    "expected": tc.get("expected_output", tc.get("expected")),
                    "actual": (stdout_text + stderr_text).strip(),
                    "time_ms": 0,
                }
                for i, tc in enumerate(test_cases)
            ]
            pass_count = 0
            parsed = {"pass_count": pass_count, "total": total, "results": results_out}
        else:
            # Normalize runner output into prompt-required shape.
            raw_results = parsed.get("results", []) or []
            results_out: list[dict[str, Any]] = []
            pass_count = 0
            for i, tc in enumerate(test_cases):
                # Try to map by explicit id; otherwise fall back to position.
                r = raw_results[i] if i < len(raw_results) else {}
                test_id = r.get("id", i)
                passed = bool(r.get("passed", False))
                if passed:
                    pass_count += 1
                results_out.append(
                    {
                        "test_id": test_id,
                        "passed": passed,
                        "expected": r.get("expected", tc.get("expected_output", tc.get("expected"))),
                        "actual": r.get("actual", ""),
                        "time_ms": r.get("time_ms", 0),
                    }
                )
            parsed = {"pass_count": pass_count, "total": len(test_cases), "results": results_out}

        # Best-effort: write to execution_results table.
        client = get_supabase_client()
        if client is not None:
            try:
                client.table("execution_results").insert(
                    {
                        "id": str(uuid.uuid4()),
                        "attempt_id": attempt_id,
                        "test_pass_count": parsed.get("pass_count", 0),
                        "test_total": parsed.get("total", len(test_cases)),
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "exit_code": exit_code,
                        "wall_time_ms": wall_time_ms,
                        "memory_kb": None,
                        "timed_out": False,
                    }
                ).execute()
            except Exception:
                pass

        # Release back to pool (reuses warm container)
        await pool.release(container)

        return {
            "attempt_id": attempt_id,
            "pass_count": parsed.get("pass_count", 0),
            "total": parsed.get("total", len(test_cases)),
            "results": parsed.get("results", []),
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": exit_code,
            "wall_time_ms": wall_time_ms,
            "timed_out": timed_out,
        }

    except asyncio.TimeoutError:
        timed_out = True

        # MUST kill the container immediately and recycle.
        await pool.recycle_on_timeout(container)

        return {
            "attempt_id": attempt_id,
            "pass_count": 0,
            "total": len(test_cases),
            "results": [],
            "stdout": "",
            "stderr": "Execution timed out",
            "exit_code": None,
            "wall_time_ms": 10000,
            "timed_out": True,
        }

