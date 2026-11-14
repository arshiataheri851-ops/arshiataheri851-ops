"""Validated request and response contracts for AtlasRAG."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=100_000)
    source: str | None = Field(default=None, max_length=500)
    metadata: dict[str, str] = Field(default_factory=dict, max_length=30)

    @field_validator("title", "text")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must contain non-whitespace characters")
        return value.strip()


class DocumentBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[DocumentIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_unique_document_ids(self) -> "DocumentBatchIn":
        identifiers = [document.document_id for document in self.documents]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("A batch cannot contain duplicate document_id values.")
        return self


class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int
    replaced_existing: bool


class BatchIngestResponse(BaseModel):
    accepted: int
    results: list[IngestResponse]


class QueryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=2_000)
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str | None
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[Citation]
    retrieval_method: str = "sqlite_fts5"


class EvaluationCase(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)
    expected_document_id: str = Field(min_length=1, max_length=120)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[EvaluationCase] = Field(min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=20)


class EvaluationResponse(BaseModel):
    cases: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float
