from app.main import create_app
from app.config import Settings
from app.store import SQLiteStore


def test_protected_routes_reject_missing_and_invalid_api_keys(client):
    assert client.get("/v1/documents", headers={}).status_code == 401
    assert client.post(
        "/v1/query", json={"question": "private content"}, headers={"X-API-Key": "wrong"}
    ).status_code == 401


def test_tenants_cannot_read_search_replace_or_delete_each_others_documents(client):
    payload = {
        "document_id": "tenant-private-doc",
        "title": "Tenant A secret",
        "text": "tenantalpha confidential retrieval phrase",
    }
    assert client.post("/v1/documents", json=payload).status_code == 201

    tenant_b = {"X-API-Key": "test-tenant-b-key-0123456789-abcdef"}
    assert client.get("/v1/documents", headers=tenant_b).json() == []
    query = client.post(
        "/v1/query", json={"question": "tenantalpha confidential retrieval"},
        headers=tenant_b,
    )
    assert query.status_code == 200
    assert query.json()["citations"] == []
    assert query.json()["grounded"] is False

    foreign_delete = client.delete("/v1/documents/tenant-private-doc", headers=tenant_b)
    assert foreign_delete.status_code == 404
    assert client.post(
        "/v1/documents",
        json={**payload, "title": "Attempted takeover", "text": "attacker replacement"},
        headers=tenant_b,
    ).status_code == 409

    original = client.post("/v1/query", json={"question": "tenantalpha confidential retrieval"})
    assert original.json()["citations"][0]["title"] == "Tenant A secret"
    assert client.get("/v1/documents").json()[0]["document_id"] == "tenant-private-doc"


def test_auth_required_configuration_fails_closed_without_tenant_keys():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(auth_required=True, tenant_api_keys_json="")
