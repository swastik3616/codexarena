from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class QuestionExample(BaseModel):
    input: str
    output: str
    explanation: str


class QuestionTestCase(BaseModel):
    id: int
    input: str
    expected_output: str


class QuestionGenPayload(BaseModel):
    title: str
    description: str
    constraints: list[str]
    examples: list[QuestionExample]
    test_cases: list[QuestionTestCase]
    hints: list[str]
    topic_tags: list[str]
    difficulty: Literal["easy", "medium", "hard"]

    @model_validator(mode="after")
    def validate_case_count(self) -> "QuestionGenPayload":
        if len(self.test_cases) != 8:
            raise ValueError("Question must contain exactly 8 test_cases")
        return self


class GenerateQuestionRequest(BaseModel):
    difficulty: Literal["easy", "medium", "hard"]
    topic_tags: list[str] = Field(default_factory=list)
    language: str = "python"


class GenerateQuestionResponse(BaseModel):
    question_id: str
    title: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    topic_tags: list[str]


