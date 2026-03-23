#!/bin/sh
set -eu

# Local security hardening:
# - filesystem is read-only except for /tmp (tmpfs)
# - no network at container level (network_disabled=True)
#
# This runner reads:
#   /tmp/submission/solution.py
#   /tmp/submission/test_cases.json
#
# It writes a single JSON object to stdout:
#   {"results": [{"id": 1, "passed": true, "actual": "...", "expected": "..."}]}

python3 - <<'PY'
import json
import os
import subprocess
import sys
import time
from pathlib import Path

submission_dir = "/tmp/submission"
solution_path = os.path.join(submission_dir, "solution.py")
test_cases_path = os.path.join(submission_dir, "test_cases.json")

# Create a tiny local `requests` stub so unit tests can call requests.get()
# without installing external dependencies (and while still failing with ConnectionError).
stub_path = "/tmp/requests.py"
Path("/tmp").mkdir(parents=True, exist_ok=True)
with open(stub_path, "w", encoding="utf-8") as f:
    f.write(
        "import urllib.request\\n"
        "class exceptions:\\n"
        "    class ConnectionError(ConnectionError):\\n"
        "        pass\\n"
        "def get(url, timeout=None, **kwargs):\\n"
        "    try:\\n"
        "        with urllib.request.urlopen(url, timeout=timeout) as r:\\n"
        "            class Resp:\\n"
        "                def __init__(self, data):\\n"
        "                    self.content = data\\n"
        "            return Resp(r.read())\\n"
        "    except Exception as e:\\n"
        "        raise ConnectionError(str(e))\\n"
    )

env = os.environ.copy()
env["PYTHONPATH"] = "/tmp" + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

with open(test_cases_path, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

results = []

for idx, tc in enumerate(test_cases):
    test_id = tc.get("id", idx + 1)
    input_data = tc.get("input", "")
    expected = tc.get("expected", "")

    start = time.monotonic()
    try:
        # Execute solution as a script so top-level infinite loops are enforced by
        # the container-level hard timeout (outside this runner).
        proc = subprocess.run(
            ["python3", solution_path],
            input=input_data,
            text=True,
            capture_output=True,
            env=env,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        actual = stdout if proc.returncode == 0 else (stderr + ("\\n" + stdout if stdout else "")).strip()
        exit_code = proc.returncode
    except Exception as e:
        actual = f"EXCEPTION:{type(e).__name__}:{e}"
        exit_code = None

    expected_str = str(expected).strip()
    actual_str = str(actual).strip()

    # For security tests, error strings vary; treat expected as substring.
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

