from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies import get_current_candidate_or_recruiter, get_current_user
from app.core.security import verify_token
from app.db.database import get_supabase_client
from app.schemas.question import GenerateQuestionRequest, GenerateQuestionResponse
from app.services.ai.question_generator import QuestionGenerator


router = APIRouter(prefix="/questions", tags=["questions"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/generate", response_model=GenerateQuestionResponse)
async def generate_question(
    payload: GenerateQuestionRequest,
    _recruiter: dict[str, Any] = Depends(get_current_user),
) -> GenerateQuestionResponse:
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

