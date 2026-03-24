#!/bin/sh
set -eu

python3 - <<'PY'
import json
import subprocess
import time

SOURCE = "/tmp/submission/solution.cpp"
BINARY = "/tmp/submission/solution"
TEST_CASES = "/tmp/test_cases.json"

with open(TEST_CASES, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

try:
    compile_proc = subprocess.run(["g++", "-O2", "-o", BINARY, SOURCE], text=True, capture_output=True)
    compile_err = (compile_proc.stderr or "").strip()
    compile_ok = compile_proc.returncode == 0
except Exception as e:
    compile_ok = False
    compile_err = f"EXCEPTION:{type(e).__name__}:{e}"

results = []
for idx, tc in enumerate(test_cases):
    test_id = tc.get("id", idx + 1)
    input_data = tc.get("input", "")
    expected = str(tc.get("expected_output", tc.get("expected", ""))).strip()
    start = time.monotonic()

    if not compile_ok:
        actual = compile_err
    else:
        try:
            proc = subprocess.run([BINARY], input=input_data, text=True, capture_output=True)
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            actual = stdout if proc.returncode == 0 else (stderr + ("\n" + stdout if stdout else "")).strip()
        except Exception as e:
            actual = f"EXCEPTION:{type(e).__name__}:{e}"

    actual_str = str(actual).strip()
    passed = expected in actual_str if expected else False
    elapsed_ms = int((time.monotonic() - start) * 1000)
    results.append({"id": test_id, "passed": passed, "actual": actual_str, "expected": expected, "time_ms": elapsed_ms})

print(json.dumps({"results": results}))
PY

