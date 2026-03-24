from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from supabase import create_client, reset_db  # type: ignore

from app.services.ai.code_evaluator import CodeEvaluator


def _seed_attempt_and_question() -> tuple[str, dict]:
    reset_db()
    supa = create_client("http://localhost", "stub")

    recruiter_id = "recruiter-1"
    room_id = "room-1"
    candidate_id = "candidate-1"
    question_id = "question-1"
    attempt_id = "attempt-1"

    supa.table("recruiters").insert({"id": recruiter_id, "email": "r@x.com", "name": "R"}).execute()
    supa.table("rooms").insert(
        {
            "id": room_id,
            "recruiter_id": recruiter_id,
            "title": "Room",
            "status": "active",
            "join_token": "tok",
            "question_id": question_id,
            "difficulty": "medium",
        }
    ).execute()
    supa.table("candidates").insert({"id": candidate_id, "room_id": room_id, "name": "C", "status": "coding"}).execute()
    q = {
        "id": question_id,
        "title": "Two Sum",
        "description": "x",
        "difficulty": "easy",
        "topic_tags": ["arrays"],
        "test_cases": [],
        "validation_status": "validated",
        "generated_by": "manual",
    }
    supa.table("questions").insert(q).execute()
    supa.table("attempts").insert({"id": attempt_id, "candidate_id": candidate_id, "question_id": question_id, "language": "python"}).execute()
    return attempt_id, q


def test_optimal_solution_scores_high():
    attempt_id, question = _seed_attempt_and_question()
    code = "def two_sum(nums, target):\n    seen={}\n    for i,n in enumerate(nums):\n        if target-n in seen: return [seen[target-n], i]\n        seen[n]=i\n    return []\n"
    out = asyncio.run(
        CodeEvaluator().evaluate(
            attempt_id=attempt_id,
            code=code,
            language="python",
            execution_result={"pass_count": 8, "total": 8},
            question=question,
        )
    )
    assert int(out["total_score"]) > 80


def test_bruteforce_efficiency_low():
    attempt_id, question = _seed_attempt_and_question()
    code = "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1,len(nums)):\n            if nums[i]+nums[j]==target: return [i,j]\n    return []\n"
    out = asyncio.run(
        CodeEvaluator().evaluate(
            attempt_id=attempt_id,
            code=code,
            language="python",
            execution_result={"pass_count": 8, "total": 8},
            question=question,
        )
    )
    assert int(out["efficiency_score"]) <= 15


def test_poor_readability_scores_low():
    attempt_id, question = _seed_attempt_and_question()
    code = "def f(a,b):\n x=[]\n for xx in range(len(a)):\n  for yy in range(len(a)):\n   if a[xx]+a[yy]==b:return [xx,yy]\n return x\n"
    out = asyncio.run(
        CodeEvaluator().evaluate(
            attempt_id=attempt_id,
            code=code,
            language="python",
            execution_result={"pass_count": 5, "total": 8},
            question=question,
        )
    )
    assert int(out["readability_score"]) <= 10


def test_zero_pass_forces_low_total():
    attempt_id, question = _seed_attempt_and_question()
    code = "def two_sum(nums, target):\n    return [0,0]\n"
    out = asyncio.run(
        CodeEvaluator().evaluate(
            attempt_id=attempt_id,
            code=code,
            language="python",
            execution_result={"pass_count": 0, "total": 8},
            question=question,
        )
    )
    assert int(out["correctness_score"]) == 0
    assert int(out["total_score"]) < 30


def test_identical_code_variance_within_ten():
    attempt_id, question = _seed_attempt_and_question()
    code = "def two_sum(nums, target):\n    seen={}\n    for i,n in enumerate(nums):\n        if target-n in seen: return [seen[target-n], i]\n        seen[n]=i\n    return []\n"
    scores = []
    for _ in range(3):
        out = asyncio.run(
            CodeEvaluator().evaluate(
                attempt_id=attempt_id,
                code=code,
                language="python",
                execution_result={"pass_count": 8, "total": 8},
                question=question,
            )
        )
        scores.append(int(out["total_score"]))
    assert max(scores) - min(scores) <= 10

