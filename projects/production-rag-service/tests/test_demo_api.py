def test_public_demo_returns_document_catalog(client):
    response = client.get("/demo/documents")
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) >= 4
    assert any(item["document_id"] == "demo-fa" for item in documents)

def test_public_demo_query_returns_grounded_citation(client):
    response = client.post("/demo/query", json={"question":"How many days can employees work remotely?"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["retrieval_method"] == "demo_bm25"
    assert body["citations"][0]["document_id"] == "demo-handbook"
    assert "three days" in body["answer"]

def test_public_demo_is_read_only_and_does_not_require_tenant_key(client):
    response = client.post("/demo/query", headers={"X-API-Key":""}, json={"question":"When should security incidents be reported?"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["document_id"] == "demo-security"

def test_public_demo_unknown_question_is_not_grounded(client):
    response = client.post("/demo/query", json={"question":"What is the recipe for a chocolate cake?"})
    assert response.status_code == 200
    assert response.json()["grounded"] is False
    assert response.json()["citations"] == []

def test_public_demo_rate_limit_is_enforced(client):
    for _ in range(20):
        assert client.get("/demo/documents").status_code == 200
    limited = client.get("/demo/documents")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
