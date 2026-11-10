import pytest
from fastapi.testclient import TestClient

from app import main
from app.retrieval import BM25Retriever
from app.store import SQLiteStore


@pytest.fixture
def client(tmp_path):
    main.store = SQLiteStore(str(tmp_path / "test.sqlite3"))
    main.retriever = BM25Retriever()
    with TestClient(main.app) as test_client:
        yield test_client
