from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    priority: Literal["balanced", "low_cost", "low_latency"] = "balanced"
    max_output_tokens: int = Field(default=512, ge=1, le=4096)
    budget_usd: float = Field(default=0.10, gt=0, le=10)


class ChatResponse(BaseModel):
    provider: str
    model: str
    output: str
    estimated_cost_usd: float
    used_fallback: bool
