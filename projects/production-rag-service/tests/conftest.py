import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.retrieval import BM25Retriever
from app.store import SQLiteStore


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_path=str(tmp_path / "test.sqlite3"))
    api = create_app(
        settings=settings,
        store=SQLiteStore(settings.database_path),
        retriever=BM25Retriever(),
    )
    with TestClient(api) as test_client:
        yield test_client
