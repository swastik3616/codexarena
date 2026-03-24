#!/bin/sh
set -eu

# python_runner.sh
# Reads /tmp/test_cases.json and runs python3 /tmp/submission/solution.py per test case.
python3 - <<'PY'
import json
import os
import subprocess
import sys
import time

SOLUTION = "/tmp/submission/solution.py"
TEST_CASES = "/tmp/test_cases.json"

with open(TEST_CASES, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

results = []

for idx, tc in enumerate(test_cases):
    test_id = tc.get("id", idx + 1)
    input_data = tc.get("input", "")
    expected = tc.get("expected_output", tc.get("expected", ""))

    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["python3", SOLUTION],
            input=input_data,
            text=True,
            capture_output=True,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        actual = stdout if proc.returncode == 0 else (stderr + ("\\n" + stdout if stdout else "")).strip()
    except Exception as e:
        actual = f"EXCEPTION:{type(e).__name__}:{e}"

    expected_str = str(expected).strip()
    actual_str = str(actual).strip()
    passed = expected_str in actual_str if expected_str else False

    elapsed_ms = int((time.monotonic() - start) * 1000)
    results.append(
        {
            "id": test_id,
            "passed": passed,
            "expected": expected_str,
            "actual": actual_str,
            "time_ms": elapsed_ms,
        }
    )

out = {"results": results}
sys.stdout.write(json.dumps(out))
PY

