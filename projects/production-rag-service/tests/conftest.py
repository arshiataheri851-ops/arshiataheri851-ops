import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.retrieval import BM25Retriever
from app.store import SQLiteStore

TEST_KEY_A = "test-tenant-a-key-0123456789-abcdef"
TEST_KEY_B = "test-tenant-b-key-0123456789-abcdef"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "test.sqlite3"),
        auth_required=True,
        tenant_api_keys_json=(
            '{"tenant-a":"' + TEST_KEY_A + '","tenant-b":"' + TEST_KEY_B + '"}'
        ),
    )
    api = create_app(
        settings=settings,
        store=SQLiteStore(settings.database_path),
        retriever=BM25Retriever(),
    )
    with TestClient(api, headers={"X-API-Key": TEST_KEY_A}) as test_client:
        yield test_client
