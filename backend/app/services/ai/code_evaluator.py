from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import redis
from pydantic import BaseModel, Field, conint

from app.core.config import settings
from app.db.database import get_supabase_client
from app.services.realtime.websocket_hub import broadcast_room_event

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "code_eval_v1.txt"


class LlmEvaluationPayload(BaseModel):
    efficiency_score: conint(ge=0, le=30)
    readability_score: conint(ge=0, le=20)
    edge_case_score: conint(ge=0, le=10)
    big_o_time: str
    big_o_space: str
    feedback: str
    suggestions: list[str] = Field(default_factory=list, min_length=1, max_length=6)


def get_redis_client() -> Any:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class CodeEvaluator:
    def __init__(self) -> None:
        self.prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    async def evaluate(
        self,
        attempt_id: str,
        code: str,
        language: str,
        execution_result: dict[str, Any],
        question: dict[str, Any],
    ) -> dict[str, Any]:
        pass_count = int(execution_result.get("pass_count", 0))
        total = max(1, int(execution_result.get("total", 0)))
        correctness_score = round((pass_count / total) * 40)

        llm_payload = await self._call_and_validate(code, language, execution_result, question)

        client = get_supabase_client()
        if client is None:
            raise ValueError("Supabase is not configured")

        eval_row = {
            "id": str(uuid.uuid4()),
            "attempt_id": str(attempt_id),
            "correctness_score": correctness_score,
            "efficiency_score": int(llm_payload.efficiency_score),
            "readability_score": int(llm_payload.readability_score),
            "edge_case_score": int(llm_payload.edge_case_score),
            "big_o_time": llm_payload.big_o_time,
            "big_o_space": llm_payload.big_o_space,
            "feedback": llm_payload.feedback,
            "suggestions": llm_payload.suggestions,
            "prompt_version": "v1",
        }
        inserted = client.table("ai_evaluations").insert(eval_row).execute().data
        stored = inserted[0] if inserted else eval_row
        stored["total_score"] = (
            int(stored.get("correctness_score", 0))
            + int(stored.get("efficiency_score", 0))
            + int(stored.get("readability_score", 0))
            + int(stored.get("edge_case_score", 0))
        )

        attempt = client.table("attempts").select("*").eq("id", str(attempt_id)).single().execute().data or {}
        candidate_id = str(attempt.get("candidate_id", ""))
        candidate = (
            client.table("candidates").select("*").eq("id", candidate_id).single().execute().data
            if candidate_id
            else None
        )
        room_id = str((candidate or {}).get("room_id", ""))

        payload = {
            "type": "ai.evaluation",
            "attempt_id": str(attempt_id),
            "candidate_id": candidate_id,
            "room_id": room_id,
            "correctness_score": int(stored["correctness_score"]),
            "efficiency_score": int(stored["efficiency_score"]),
            "readability_score": int(stored["readability_score"]),
            "edge_case_score": int(stored["edge_case_score"]),
            "total_score": int(stored["total_score"]),
            "feedback": stored.get("feedback"),
        }

        try:
            get_redis_client().publish(f"room:{room_id}:execution", json.dumps(payload))
        except Exception:
            pass
        if room_id:
            await broadcast_room_event(room_id=room_id, payload=payload, target_role="recruiter")
        return stored

    async def _call_and_validate(
        self, code: str, language: str, execution_result: dict[str, Any], question: dict[str, Any]
    ) -> LlmEvaluationPayload:
        last_error: Exception | None = None
        for _ in range(2):
            try:
                raw = await self._call_gemini_or_fallback(code, language, execution_result, question)
                return LlmEvaluationPayload.model_validate(raw)
            except Exception as exc:
                last_error = exc
                continue
        raise ValueError(f"Failed to parse evaluation response: {last_error}")

    async def _call_gemini_or_fallback(
        self, code: str, language: str, execution_result: dict[str, Any], question: dict[str, Any]
    ) -> dict[str, Any]:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._fallback_eval(code=code, language=language, execution_result=execution_result)

        prompt = self.prompt_template.format(
            problem_title=question.get("title", "Coding Problem"),
            language=language,
            code=code,
            test_pass_count=int(execution_result.get("pass_count", 0)),
            test_total=int(execution_result.get("total", 0)),
        )
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1000},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params={"key": api_key}, json=body)
            resp.raise_for_status()
            out = resp.json()
        text = out.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _fallback_eval(self, code: str, language: str, execution_result: dict[str, Any]) -> dict[str, Any]:
        # Deterministic local heuristic for tests/dev when Gemini key is absent.
        pass_count = int(execution_result.get("pass_count", 0))
        total = max(1, int(execution_result.get("total", 0)))
        ratio = pass_count / total

        lc = code.lower()
        has_bad_names = any(token in lc for token in ["tmp", "aaa", "bbb", "xx", "yy"])
        has_comments = ("#" in code) or ("//" in code) or ("/*" in code)
        brute_force = ("for" in lc and lc.count("for") >= 2) or "o(n^2)" in lc or "n*n" in lc
        has_edge_checks = any(k in lc for k in ["if not", "len(", "null", "none", "empty", "return []"])

        efficiency = 24
        if brute_force:
            efficiency = 10
        elif ratio < 0.5:
            efficiency = 12

        readability = 16
        if has_bad_names and not has_comments:
            readability = 8
        elif not has_comments:
            readability = 11

        edge_case = 7 if has_edge_checks else 4
        if ratio == 0:
            edge_case = min(edge_case, 3)

        return {
            "efficiency_score": max(0, min(30, efficiency)),
            "readability_score": max(0, min(20, readability)),
            "edge_case_score": max(0, min(10, edge_case)),
            "big_o_time": "O(n^2)" if brute_force else "O(n)",
            "big_o_space": "O(n)",
            "feedback": f"The {language} solution passes {pass_count}/{total} tests. It is functional but can be improved in clarity and edge-case handling.",
            "suggestions": [
                "Add clearer variable names and small helper functions.",
                "Document assumptions and edge cases with concise comments.",
                "Optimize hotspot loops and avoid repeated scans.",
            ],
        }

