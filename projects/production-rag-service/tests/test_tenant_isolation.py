import pytest
from pydantic import ValidationError

from app.config import Settings


def test_all_protected_routes_reject_missing_and_invalid_api_keys(client):
    no_key = {"X-API-Key": ""}
    bad_key = {"X-API-Key": "wrong"}
    assert client.get("/health").status_code == 200
    assert client.get("/", headers={}).status_code == 200
    assert client.get("/v1/documents", headers=no_key).status_code == 401
    assert client.post(
        "/v1/documents", json={"document_id": "x", "title": "X", "text": "test"}, headers=bad_key
    ).status_code == 401
    assert client.post("/v1/documents/batch", json={"documents": [{"document_id": "x", "title": "X", "text": "test"}]}, headers=no_key).status_code == 401
    assert client.delete("/v1/documents/x", headers=no_key).status_code == 401
    assert client.post(
        "/v1/query", json={"question": "private content"}, headers=bad_key
    ).status_code == 401
    assert client.post(
        "/v1/evaluate", json={"cases": [{"question": "private content", "expected_document_id": "x"}]},
        headers=no_key,
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

    with pytest.raises(ValidationError):
        Settings(auth_required=True, tenant_api_keys_json="")


def test_tenant_api_keys_must_be_strong_unique_ascii_values():
    weak = '{"tenant-a":"too-short"}'
    duplicate = (
        '{"tenant-a":"same-secret-value-that-is-at-least-32-chars",'
        '"tenant-b":"same-secret-value-that-is-at-least-32-chars"}'
    )
    non_ascii = '{"tenant-a":"کلید-این-کلید-باید-طولانی-باشد-برای-تست"}'
    for mapping in (weak, duplicate, non_ascii):
        with pytest.raises(ValidationError):
            Settings(auth_required=True, tenant_api_keys_json=mapping)


def test_metrics_endpoint_requires_its_own_secret_and_exposes_no_tenant_content(client):
    assert client.get("/metrics").status_code == 401
    response = client.get(
        "/metrics",
        headers={"Authorization": "Bearer test-metrics-token-0123456789-abcdef"},
    )
    assert response.status_code == 200
    assert "atlasrag_http_requests_total" in response.text
    assert "test-tenant-a-key" not in response.text


def test_audit_log_omits_api_keys_and_document_content(client, caplog):
    caplog.set_level("INFO", logger="atlasrag.audit")
    secret_text = "private-customer-content-should-never-enter-audit-log"
    secret_key = "test-tenant-a-key-0123456789-abcdef"
    response = client.post(
        "/v1/documents",
        json={"document_id": "private-doc-ref", "title": "Private", "text": secret_text},
        headers={"X-API-Key": secret_key},
    )
    assert response.status_code == 201
    assert '"event":"document.upsert"' in caplog.text
    assert secret_text not in caplog.text
    assert secret_key not in caplog.text
    assert "private-doc-ref" not in caplog.text
