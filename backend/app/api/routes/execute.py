from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_candidate, get_current_candidate_or_recruiter
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.logging import get_logger
from app.core.metrics import execution_jobs_total
from app.db.database import get_supabase_client
from app.schemas.execution import (
    ExecuteQueuedResponse,
    ExecuteResultResponse,
    ExecuteRequest,
    ExecuteRunningResponse,
)
from app.workers.execution_worker import execute_submission

router = APIRouter(prefix="/execute", tags=["execute"])
logger = get_logger(service="api")


@router.post("", response_model=ExecuteQueuedResponse)
async def execute(
    payload: ExecuteRequest,
    current_candidate: dict[str, Any] = Depends(get_current_candidate),
) -> ExecuteQueuedResponse:
    candidate_id = current_candidate["id"]

    redis_client = get_redis_client()

    # Rate limit: max 1 request per 5 seconds per candidate_id
    rate_key = f"exec_rate:{candidate_id}"
    count = redis_client.incr(rate_key)
    if count == 1:
        redis_client.expire(rate_key, 5)
    if count > 1:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "5"},
        )

    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    attempt_res = client.table("attempts").select("*").eq("id", payload.attempt_id).single().execute()
    attempt = attempt_res.data
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if str(attempt.get("candidate_id")) != str(candidate_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    question_id = attempt.get("question_id")
    question_res = client.table("questions").select("*").eq("id", question_id).single().execute()
    question = question_res.data
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    test_cases = question.get("test_cases", [])

    cand_res = client.table("candidates").select("*").eq("id", candidate_id).single().execute()
    cand_row = cand_res.data
    if not cand_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    room_id = cand_row.get("room_id")

    # Update attempt
    client.table("attempts").update({"final_code": payload.code, "language": payload.language}).eq("id", payload.attempt_id).execute()

    job_id = str(uuid.uuid4())
    job_status_key = f"exec_job:{job_id}:status"
    job_attempt_key = f"exec_job:{job_id}:attempt_id"

    redis_client.set(job_attempt_key, payload.attempt_id)
    redis_client.set(job_status_key, "queued")

    job_payload: dict[str, Any] = {
        "attempt_id": payload.attempt_id,
        "candidate_id": candidate_id,
        "code": payload.code,
        "language": payload.language,
        "test_cases": test_cases,
        "room_id": room_id,
    }
    # Store payload so GET can run/retrieve status.
    payload_key = f"exec_job:{job_id}:payload"
    redis_client.set(payload_key, json.dumps(job_payload))
    logger.info("job_enqueued", attempt_id=payload.attempt_id, language=payload.language, job_id=job_id)
    execution_jobs_total.labels("enqueued").inc()

    return ExecuteQueuedResponse(job_id=job_id, status="queued", message="Execution queued")


@router.get("/{job_id}", response_model=ExecuteResultResponse | ExecuteRunningResponse)
async def get_execute_status(
    job_id: str,
    _current: dict[str, Any] = Depends(get_current_candidate_or_recruiter),
) -> Any:
    redis_client = get_redis_client()

    status_key = f"exec_job:{job_id}:status"
    attempt_key = f"exec_job:{job_id}:attempt_id"

    job_status = redis_client.get(status_key)
    if not job_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job_status == "queued":
        # Scaffold mode: execute on first poll to keep POST fast.
        payload_key = f"exec_job:{job_id}:payload"
        payload_raw = redis_client.get(payload_key)
        if not payload_raw:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job payload not found")

        job_payload = json.loads(payload_raw)
        ctx = SimpleNamespace(job_id=job_id)
        await execute_submission(ctx, job_payload)
        job_status = redis_client.get(status_key)

    if job_status != "complete":
        return ExecuteRunningResponse(status="running", job_id=job_id)

    attempt_id = redis_client.get(attempt_key)
    if not attempt_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt mapping not found")

    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    exec_res = client.table("execution_results").select("*").eq("attempt_id", attempt_id).single().execute()
    exec_row = exec_res.data
    if not exec_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution result not found")

    stdout_json = exec_row.get("stdout")
    parsed: dict[str, Any] = {}
    try:
        if isinstance(stdout_json, str) and stdout_json.strip():
            parsed = json.loads(stdout_json)
    except Exception:
        parsed = {}

    raw_results = parsed.get("results", []) or []
    results_out = []
    for r in raw_results:
        results_out.append(
            {
                "test_id": r.get("id", r.get("test_id")),
                "passed": bool(r.get("passed")),
                "actual": str(r.get("actual", "")),
                "time_ms": int(r.get("time_ms", 0)),
            }
        )

    return ExecuteResultResponse(
        status="complete",
        pass_count=int(exec_row.get("test_pass_count") or 0),
        total=int(exec_row.get("test_total") or 0),
        stdout=exec_row.get("stdout"),
        stderr=exec_row.get("stderr"),
        wall_time_ms=exec_row.get("wall_time_ms"),
        timed_out=bool(exec_row.get("timed_out") or False),
        results=results_out,
    )

