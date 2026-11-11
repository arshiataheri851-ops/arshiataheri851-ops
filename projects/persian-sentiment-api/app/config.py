from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_ID = "HooshvareLab/bert-fa-base-uncased-sentiment-snappfood"
DEFAULT_MODEL_REVISION = "8c5d0be5517c4bd5e26f785b1ad60b394a80de07"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SENTIMENT_",
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
    )

    model_id: str = DEFAULT_MODEL_ID
    model_revision: str = DEFAULT_MODEL_REVISION
    max_sequence_length: int = Field(default=512, ge=8, le=512)


@lru_cache
def get_settings() -> Settings:
    return Settings()
