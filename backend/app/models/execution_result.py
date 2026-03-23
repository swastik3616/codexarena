from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ExecutionResult(BaseModel):
    id: UUID
    attempt_id: UUID
    test_pass_count: int = 0
    test_total: int = 0
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    wall_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    timed_out: Optional[bool] = False
    executed_at: Optional[datetime] = None

