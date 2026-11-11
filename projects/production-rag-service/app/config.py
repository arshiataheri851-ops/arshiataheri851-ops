from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    database_path: str = "./data/rag.sqlite3"
    chunk_size: int = Field(default=700, ge=50, le=5_000)
    chunk_overlap: int = Field(default=100, ge=0, le=4_999)
    max_document_chars: int = Field(default=100_000, ge=1_000, le=1_000_000)
    max_query_chars: int = Field(default=2_000, ge=2, le=10_000)
    default_top_k: int = Field(default=5, ge=1, le=20)
    max_top_k: int = Field(default=20, ge=1, le=20)
    min_relevance_score: float = Field(default=0.01, ge=0.0)

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.default_top_k > self.max_top_k:
            raise ValueError("default_top_k cannot exceed max_top_k")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
