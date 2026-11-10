from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    database_path: str = "./data/rag.sqlite3"
    chunk_size: int = 700
    chunk_overlap: int = 100
    max_document_chars: int = 100_000
    max_query_chars: int = 2_000
    default_top_k: int = 5
    max_top_k: int = 20
    min_relevance_score: float = 0.01


@lru_cache
def get_settings() -> Settings:
    return Settings()
