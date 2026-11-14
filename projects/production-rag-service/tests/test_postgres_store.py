import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.postgres_store import PostgresStore
from app.store import SQLiteStore, TenantDocumentConflict

DATABASE_URL = os.getenv("RAG_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="RAG_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
def postgres_store():
    store = PostgresStore(DATABASE_URL)
    yield store
    store.close()


def test_postgres_health_persian_fts_and_tenant_isolation(postgres_store):
    suffix = uuid4().hex
    tenant_a = f"tenant_a_{suffix}"
    tenant_b = f"tenant_b_{suffix}"
    document_id = f"postgres-{suffix}"
    try:
        postgres_store.upsert_document(
            document_id,
            "Persian database guide",
            "test://postgres",
            {"kind": "integration"},
            ["پایگاه داده رابطه‌ای برای ذخیره و جست‌وجوی اطلاعات استفاده می‌شود."],
            tenant_id=tenant_a,
        )
        assert postgres_store.health_check() is True
        results = postgres_store.search_chunks(
            "پایگاه داده جست‌وجو", 5, tenant_id=tenant_a
        )
        assert results
        assert results[0]["document_id"] == document_id
        assert results[0]["metadata"] == {"kind": "integration"}
        assert postgres_store.search_chunks(
            "پایگاه داده جست‌وجو", 5, tenant_id=tenant_b
        ) == []
        assert postgres_store.count_documents(tenant_a) == 1
        assert postgres_store.count_documents(tenant_b) == 0
        assert postgres_store.delete_document(document_id, tenant_id=tenant_b) is False
    finally:
        postgres_store.delete_document(document_id, tenant_id=tenant_a)


def test_postgres_batch_is_atomic_on_cross_tenant_collision(postgres_store):
    suffix = uuid4().hex
    owner = f"owner_{suffix}"
    attacker = f"attacker_{suffix}"
    foreign_id = f"foreign-{suffix}"
    new_id = f"new-{suffix}"
    postgres_store.upsert_document(
        foreign_id, "Private", None, {}, ["private tenant content"], tenant_id=owner
    )
    try:
        with pytest.raises(TenantDocumentConflict):
            postgres_store.upsert_documents_batch(
                [
                    {
                        "document_id": new_id,
                        "title": "Would be inserted",
                        "source": None,
                        "metadata": {},
                        "chunks": ["this must roll back"],
                    },
                    {
                        "document_id": foreign_id,
                        "title": "Attempted takeover",
                        "source": None,
                        "metadata": {},
                        "chunks": ["must not overwrite owner data"],
                    },
                ],
                tenant_id=attacker,
            )
        assert postgres_store.count_documents(attacker) == 0
        assert postgres_store.search_chunks(
            "private tenant content", 3, tenant_id=owner
        )[0]["document_id"] == foreign_id
    finally:
        postgres_store.delete_document(foreign_id, tenant_id=owner)
        postgres_store.delete_document(new_id, tenant_id=attacker)


def test_sqlite_migration_preserves_tenant_documents_and_search(postgres_store, tmp_path):
    suffix = uuid4().hex
    tenant_id = f"migrated_{suffix}"
    document_id = f"migrated-doc-{suffix}"
    sqlite_path = tmp_path / "legacy.sqlite3"
    source = SQLiteStore(str(sqlite_path))
    source.upsert_document(
        document_id,
        "Migrated Persian policy",
        "archive://legacy",
        {"origin": "sqlite"},
        ["مهاجرت داده قدیمی و بازیابی اطلاعات با جست‌وجوی ایندکس‌شده."],
        tenant_id=tenant_id,
    )

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "migrate_sqlite_to_postgres.py"
    environment = {**os.environ, "RAG_DATABASE_URL": DATABASE_URL}
    subprocess.run(
        [sys.executable, str(script_path), "--sqlite-path", str(sqlite_path)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    try:
        rows = postgres_store.search_chunks(
            "مهاجرت داده بازیابی", 5, tenant_id=tenant_id
        )
        assert rows
        assert rows[0]["document_id"] == document_id
        assert rows[0]["metadata"] == {"origin": "sqlite"}
        assert postgres_store.count_documents(tenant_id) == 1
    finally:
        postgres_store.delete_document(document_id, tenant_id=tenant_id)


def test_fastapi_application_uses_postgres_backend_and_closes_pool(postgres_store):
    suffix = uuid4().hex
    tenant_id = f"api_tenant_{suffix}"
    document_id = f"api-doc-{suffix}"
    api_key = f"integration-api-key-{suffix}-0123456789"
    settings = Settings(
        auth_required=True,
        tenant_api_keys_json=json.dumps({tenant_id: api_key}),
        database_url=DATABASE_URL,
    )
    application = create_app(settings=settings)
    try:
        with TestClient(application) as client:
            assert client.get("/health").status_code == 200
            ingest = client.post(
                "/v1/documents",
                headers={"X-API-Key": api_key},
                json={
                    "document_id": document_id,
                    "title": "PostgreSQL application smoke",
                    "source": "test://application",
                    "text": "A PostgreSQL application stores indexed tenant evidence.",
                },
            )
            assert ingest.status_code == 201
            result = client.post(
                "/v1/query",
                headers={"X-API-Key": api_key},
                json={"question": "PostgreSQL indexed tenant evidence", "top_k": 3},
            )
            assert result.status_code == 200
            assert result.json()["retrieval_method"] == "postgresql_fts"
            assert result.json()["citations"][0]["document_id"] == document_id
    finally:
        postgres_store.delete_document(document_id, tenant_id=tenant_id)


def test_postgres_hybrid_retrieval_finds_semantic_match_without_lexical_overlap():
    suffix = uuid4().hex
    tenant_id = f"semantic_{suffix}"
    document_id = f"semantic-doc-{suffix}"
    expected_vector = [1.0] + [0.0] * 383
    store = PostgresStore(
        DATABASE_URL,
        passage_embedding_function=lambda texts: [expected_vector for _ in texts],
        query_embedding_function=lambda query: expected_vector,
    )
    try:
        store.upsert_document(
            document_id,
            "موقعیت دفتر",
            "test://semantic",
            {"kind": "semantic-integration"},
            ["نشانی محل کار در خیابان اصلی قرار دارد."],
            tenant_id=tenant_id,
        )
        results = store.search_chunks(
            "where is the office location", 5, tenant_id=tenant_id
        )
        assert store.retrieval_method == "postgresql_hybrid_rrf"
        assert results
        assert results[0]["document_id"] == document_id
        assert results[0]["score"] > 0
        assert store.search_chunks(
            "where is the office location", 5, tenant_id=f"other_{suffix}"
        ) == []
    finally:
        store.delete_document(document_id, tenant_id=tenant_id)
        store.close()
