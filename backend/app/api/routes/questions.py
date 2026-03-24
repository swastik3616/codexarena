from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies import get_current_candidate_or_recruiter, get_current_user
from app.core.redis_client import get_redis_client
from app.core.security import verify_token
from app.db.database import get_supabase_client
from app.schemas.question import GenerateQuestionRequest, GenerateQuestionResponse
from app.services.ai.question_generator import QuestionGenerator


router = APIRouter(prefix="/questions", tags=["questions"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _rate_limit(redis_client: Any, key: str, *, limit: int, ttl_seconds: int) -> None:
    if not hasattr(redis_client, "incr"):
        return
    try:
        count = redis_client.incr(key)
        if count == 1 and hasattr(redis_client, "expire"):
            redis_client.expire(key, ttl_seconds)
        if count > limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        return


@router.post("/generate", response_model=GenerateQuestionResponse)
async def generate_question(
    payload: GenerateQuestionRequest,
    recruiter: dict[str, Any] = Depends(get_current_user),
) -> GenerateQuestionResponse:
    redis_client = get_redis_client()
    rid = str(recruiter.get("id"))
    rl_key = f"rl:qgen:{rid}"
    _rate_limit(redis_client, rl_key, limit=10, ttl_seconds=3600)

    generator = QuestionGenerator()
    question = await generator.generate(
        difficulty=payload.difficulty,
        topic_tags=payload.topic_tags,
        language=payload.language,
    )
    return GenerateQuestionResponse(
        question_id=str(question["id"]),
        title=question["title"],
        description=question["description"],
        difficulty=question["difficulty"],
        topic_tags=question.get("topic_tags", []),
    )


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    _auth: dict[str, Any] = Depends(get_current_candidate_or_recruiter),
    token: str = Depends(oauth2_scheme),
) -> dict[str, Any]:
    payload = verify_token(token)
    role = payload.get("role") or "recruiter"

    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    res = client.table("questions").select("*").eq("id", question_id).single().execute()
    row = res.data
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    out = dict(row)
    test_cases = out.get("test_cases") or []
    if role == "candidate":
        sanitized = []
        for tc in test_cases:
            sanitized.append({"id": tc.get("id"), "input": tc.get("input")})
        out["test_cases"] = sanitized
    return out

