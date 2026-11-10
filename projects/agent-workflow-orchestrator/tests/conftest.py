import pytest
from fastapi.testclient import TestClient
from app import main
from app.engine import WorkflowEngine
from app.store import WorkflowStore


@pytest.fixture
def client(tmp_path):
    main.store = WorkflowStore(str(tmp_path / "test.sqlite3"))
    main.engine = WorkflowEngine(main.store)
    with TestClient(main.app) as test_client:
        yield test_client
