import json
import re
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    database_path: str = "./data/rag.sqlite3"
    auth_required: bool = True
    tenant_api_keys_json: str = ""
    chunk_size: int = Field(default=700, ge=50, le=5_000)
    chunk_overlap: int = Field(default=100, ge=0, le=4_999)
    max_document_chars: int = Field(default=100_000, ge=1_000, le=1_000_000)
    max_query_chars: int = Field(default=2_000, ge=2, le=10_000)
    default_top_k: int = Field(default=5, ge=1, le=20)
    max_top_k: int = Field(default=20, ge=1, le=20)
    min_relevance_score: float = Field(default=0.01, ge=0.0)

    @property
    def tenant_api_keys(self) -> dict[str, str]:
        if not self.tenant_api_keys_json:
            return {}
        return json.loads(self.tenant_api_keys_json)

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.default_top_k > self.max_top_k:
            raise ValueError("default_top_k cannot exceed max_top_k")
        try:
            keys = json.loads(self.tenant_api_keys_json) if self.tenant_api_keys_json else {}
        except json.JSONDecodeError as exc:
            raise ValueError("tenant_api_keys_json must be valid JSON") from exc
        if not isinstance(keys, dict):
            raise ValueError("tenant_api_keys_json must be a JSON object of tenant_id to API key")
        for tenant_id, api_key in keys.items():
            if not isinstance(tenant_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", tenant_id):
                raise ValueError("tenant IDs must contain only letters, numbers, underscores, or hyphens")
            if not isinstance(api_key, str) or len(api_key) < 32:
                raise ValueError(f"API key for tenant '{tenant_id}' must be at least 32 characters")
        if self.auth_required and not keys:
            raise ValueError("Authentication is enabled but no tenant API keys are configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
