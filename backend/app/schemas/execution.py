from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    attempt_id: str
    language: str
    code: str


class ExecuteQueuedResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
    message: str = "Execution queued"


class ExecuteRunningResponse(BaseModel):
    status: Literal["running"]
    job_id: str


class ExecuteResultItem(BaseModel):
    test_id: int | str
    passed: bool
    actual: str
    time_ms: int


class ExecuteResultResponse(BaseModel):
    status: Literal["complete"]
    pass_count: int
    total: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    wall_time_ms: int | None = None
    timed_out: bool = False
    results: list[ExecuteResultItem]

