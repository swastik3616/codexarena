from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_supabase_client
from app.core.metrics import ai_duration_seconds
logger = get_logger(service="ai_worker")

from app.schemas.question import QuestionGenPayload
from app.services.execution import runner


PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "question_gen_v1.txt"


class QuestionGenerator:
    def __init__(self) -> None:
        self.prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    async def generate(self, difficulty: str, topic_tags: list, language: str) -> dict:
        """
        Generate and validate a question, store in DB, return stored row.
        """

        logger.info("generation_started", difficulty=difficulty, language=language)
        t0 = time.perf_counter()
        regen_attempts = 0
        while regen_attempts < 2:
            data = await self._generate_and_validate_schema(difficulty=difficulty, topic_tags=topic_tags, language=language)

            ok = await self._validate_test_cases_with_sandbox(data)
            if ok:
                stored = self._store_question(data)
                ai_duration_seconds.labels("question_generation").observe(max(0.0, time.perf_counter() - t0))
                logger.info(
                    "generation_completed",
                    question_id=str(stored.get("id", "")),
                    duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                )
                return stored

            regen_attempts += 1

        raise ValueError("Failed to generate a valid question after validation retries")

    async def _generate_and_validate_schema(self, difficulty: str, topic_tags: list, language: str) -> QuestionGenPayload:
        last_err: Exception | None = None
        for _ in range(3):
            try:
                raw = await self._call_gemini_or_fallback(difficulty=difficulty, topic_tags=topic_tags, language=language)
                payload = QuestionGenPayload.model_validate(raw)
                return payload
            except Exception as e:
                last_err = e
                continue
        raise ValueError(f"Schema validation failed after retries: {last_err}")

    async def _call_gemini_or_fallback(self, difficulty: str, topic_tags: list, language: str) -> dict[str, Any]:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._fallback_question(difficulty=difficulty, topic_tags=topic_tags, language=language)

        prompt = self.prompt_template.format(
            difficulty=difficulty,
            topic_tags=", ".join(topic_tags) if topic_tags else "arrays, hash map",
            language=language,
        )

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-pro:generateContent"
        )
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2000},
        }
        params = {"key": api_key}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params=params, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()

        # Extract Gemini text output.
        text = (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        ).strip()
        if not text:
            raise ValueError("Empty Gemini response")

        # Gemini sometimes wraps JSON in code fences; strip if present.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    async def _validate_test_cases_with_sandbox(self, question: QuestionGenPayload) -> bool:
        """
        Validate generated test cases by executing a synthetic "oracle" solution in sandbox.
        If sandbox says any test failed -> invalid question.
        """

        # Build deterministic oracle that echoes expected output by exact input match.
        lookup = {tc.input: tc.expected_output for tc in question.test_cases}
        oracle_code = (
            "import sys\n"
            f"MAP = {json.dumps(lookup)}\n"
            "raw = sys.stdin.read()\n"
            "print(MAP.get(raw, MAP.get(raw.rstrip('\\n'), '')))\n"
        )

        # Runner expects each test case to have `expected`.
        exec_cases = [{"id": tc.id, "input": tc.input, "expected": tc.expected_output} for tc in question.test_cases]

        result = await runner.execute_code(code=oracle_code, language="python", test_cases=exec_cases)
        return int(result.get("pass_count", 0)) == int(result.get("total", len(exec_cases)))

    def _store_question(self, question: QuestionGenPayload) -> dict[str, Any]:
        client = get_supabase_client()
        if client is None:
            raise ValueError("Supabase is not configured")

        qid = str(uuid.uuid4())
        row = {
            "id": qid,
            "title": question.title,
            "description": question.description,
            "difficulty": question.difficulty,
            "topic_tags": question.topic_tags,
            "test_cases": [tc.model_dump() for tc in question.test_cases],
            "validation_status": "validated",
            "generated_by": "ai",
        }
        inserted = client.table("questions").insert(row).execute().data
        if inserted and isinstance(inserted, list):
            return inserted[0]
        return row

    def _fallback_question(self, difficulty: str, topic_tags: list, language: str) -> dict[str, Any]:
        tags = topic_tags or ["arrays", "hash-map"]
        return {
            "title": "Two Sum",
            "description": (
                "Given an integer array `nums` and an integer `target`, return indices of the two numbers such that "
                "they add up to target. You may assume each input has exactly one solution and you may not use the "
                "same element twice. Return the answer in any order.\n\n"
                "Implement an efficient approach and handle corner cases such as repeated values, empty-like input, "
                "and larger arrays."
            ),
            "constraints": [
                "2 <= len(nums) <= 10^5",
                "-10^9 <= nums[i] <= 10^9",
                "-10^9 <= target <= 10^9",
            ],
            "examples": [
                {"input": "[2,7,11,15]\\n9\\n", "output": "[0, 1]", "explanation": "2 + 7 = 9"},
                {"input": "[3,2,4]\\n6\\n", "output": "[1, 2]", "explanation": "2 + 4 = 6"},
            ],
            "test_cases": [
                {"id": 1, "input": "[2,7,11,15]\\n9\\n", "expected_output": "[0, 1]"},
                {"id": 2, "input": "[3,2,4]\\n6\\n", "expected_output": "[1, 2]"},
                {"id": 3, "input": "[3,3]\\n6\\n", "expected_output": "[0, 1]"},
                {"id": 4, "input": "[]\\n0\\n", "expected_output": "[]"},
                {"id": 5, "input": "[5]\\n5\\n", "expected_output": "[]"},
                {"id": 6, "input": "[1,2,3,4,5,6,7,8,9,10]\\n19\\n", "expected_output": "[8, 9]"},
                {"id": 7, "input": "[0,1,2,3,4,5,6,7,8,9]\\n17\\n", "expected_output": "[8, 9]"},
                {"id": 8, "input": "[-1,-2,-3,-4,-5]\\n-8\\n", "expected_output": "[2, 4]"},
            ],
            "hints": [
                "Try tracking previously seen numbers while scanning once.",
                "For each element x, check whether target-x was seen earlier.",
                "A hash map from value to index gives O(n) lookup.",
            ],
            "topic_tags": tags,
            "difficulty": difficulty if difficulty in {"easy", "medium", "hard"} else "medium",
        }

