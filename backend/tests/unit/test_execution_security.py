from __future__ import annotations

import asyncio
import time
import unittest
from typing import Any

import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so `import app...` works.
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _docker_available() -> bool:
    try:
        import docker

        c = docker.from_env()
        c.ping()
        return True
    except Exception:
        return False


class ExecutionSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not _docker_available():
            raise unittest.SkipTest("Docker daemon is not available in this environment.")

    def _run(self, code: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        from app.services.execution.runner import execute_code

        return asyncio.run(execute_code(code=code, language="python", test_cases=test_cases))

    def test_network_blocked(self) -> None:
        code = r"""
import requests
def main():
    try:
        requests.get("http://example.com", timeout=1)
        print("UNEXPECTED")
    except Exception as e:
        print(type(e).__name__)

if __name__ == "__main__":
    main()
"""
        start = time.monotonic()
        res = self._run(code, [{"id": 1, "input": "", "expected": "ConnectionError"}])
        elapsed = time.monotonic() - start
        self.assertLessEqual(elapsed, 11.0)
        self.assertFalse(res.get("timed_out", False))
        self.assertEqual(res["results"][0]["passed"], True)

    def test_timeout_enforced(self) -> None:
        code = r"""
while True:
    pass
"""
        start = time.monotonic()
        res = self._run(code, [{"id": 1, "input": "", "expected": ""}])
        elapsed = time.monotonic() - start
        self.assertLessEqual(elapsed, 11.0)
        self.assertTrue(res.get("timed_out", False))

    def test_memory_limit(self) -> None:
        code = r"""
# Allocate ~200MB; container memory limit should kill the process.
a = bytearray(200 * 1024 * 1024)
print("UNEXPECTED")
"""
        start = time.monotonic()
        res = self._run(code, [{"id": 1, "input": "", "expected": "EXIT:"}])
        elapsed = time.monotonic() - start
        self.assertLessEqual(elapsed, 11.0)
        self.assertFalse(res.get("timed_out", False))

        # We expect the actual output to indicate abnormal termination.
        actual = res["results"][0]["actual"]
        self.assertTrue(("EXIT:" in actual) or ("MemoryError" in actual) or actual)

    def test_fork_bomb(self) -> None:
        code = r"""
import os
try:
    os.system(':(){ :|:& };:')
except Exception:
    pass
print("DONE")
"""
        start = time.monotonic()
        res = self._run(code, [{"id": 1, "input": "", "expected": "DONE"}])
        elapsed = time.monotonic() - start
        self.assertLessEqual(elapsed, 11.0)
        self.assertFalse(res.get("timed_out", False))

    def test_filesystem_readonly(self) -> None:
        code = r"""
try:
    with open("/etc/passwd", "w") as f:
        f.write("x")
    print("UNEXPECTED")
except Exception as e:
    print(type(e).__name__)
"""
        res = self._run(code, [{"id": 1, "input": "", "expected": "PermissionError"}])
        self.assertFalse(res.get("timed_out", False))
        self.assertEqual(res["results"][0]["passed"], True)

    def test_correct_python(self) -> None:
        # Input format:
        #   line1: JSON array of nums
        #   line2: target integer
        code = r"""
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
        res = self._run(
            code,
            [
                {
                    "id": 1,
                    "input": "[2,7,11,15]\n9\n",
                    "expected": "[0, 1]",
                }
            ],
        )
        self.assertFalse(res.get("timed_out", False))
        self.assertEqual(res["results"][0]["passed"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

