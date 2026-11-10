from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_ID = "HooshvareLab/bert-fa-base-uncased-sentiment-snappfood"
DEFAULT_MODEL_REVISION = "8c5d0be5517c4bd5e26f785b1ad60b394a80de07"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SENTIMENT_",
        env_file=".env",
        extra="ignore",
    )

    model_id: str = DEFAULT_MODEL_ID
    model_revision: str = DEFAULT_MODEL_REVISION
    max_input_chars: int = 4000
    max_batch_size: int = 32
    max_sequence_length: int = 512


@lru_cache
def get_settings() -> Settings:
    return Settings()
