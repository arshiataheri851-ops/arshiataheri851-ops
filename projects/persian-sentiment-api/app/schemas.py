from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SentimentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=4000, description="Persian text to classify")

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value:
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class BatchSentimentInput(BaseModel):
    items: list[SentimentInput] = Field(min_length=1, max_length=32)


class SentimentScores(BaseModel):
    positive: float = Field(ge=0.0, le=1.0)
    negative: float = Field(ge=0.0, le=1.0)


class SentimentOutput(BaseModel):
    text: str
    normalized_text: str
    sentiment: Literal["positive", "negative"]
    confidence: float = Field(ge=0.0, le=1.0)
    scores: SentimentScores
    model: str
    language: Literal["fa"] = "fa"


class BatchSentimentOutput(BaseModel):
    predictions: list[SentimentOutput]
    count: int
