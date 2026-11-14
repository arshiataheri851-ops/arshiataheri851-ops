import os
from uuid import uuid4

import pytest

from app.postgres_store import PostgresStore
from app.store import TenantDocumentConflict

DATABASE_URL = os.getenv("RAG_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="RAG_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
def postgres_store():
    store = PostgresStore(DATABASE_URL)
    yield store


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
