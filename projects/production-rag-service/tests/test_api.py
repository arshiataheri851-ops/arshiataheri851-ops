def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_query_and_citations(client):
    payload = {
        "document_id": "db-guide", "title": "Database Guide", "source": "internal://db",
        "text": "Database indexes improve lookup speed. Indexes reduce the amount of data scanned by a query."
    }
    ingest = client.post("/v1/documents", json=payload)
    assert ingest.status_code == 201
    assert ingest.json()["chunks_created"] >= 1
    result = client.post("/v1/query", json={
        "question": "How do database indexes improve query lookup?"
    })
    assert result.status_code == 200
    body = result.json()
    assert body["grounded"] is True
    assert body["citations"][0]["document_id"] == "db-guide"
    assert "Indexes" in body["answer"] or "indexes" in body["answer"]


def test_unknown_question_is_explicitly_ungrounded(client):
    client.post("/v1/documents", json={
        "document_id": "one", "title": "One", "text": "This document is about database indexes."
    })
    result = client.post("/v1/query", json={"question": "Explain marine biology"})
    assert result.status_code == 200
    assert result.json()["grounded"] is False
    assert result.json()["citations"] == []


def test_document_upsert_replaces_chunks(client):
    base = {"document_id": "same", "title": "Old", "text": "Old content about databases."}
    assert client.post("/v1/documents", json=base).json()["replaced_existing"] is False
    base.update(title="New", text="New content about networking.")
    assert client.post("/v1/documents", json=base).json()["replaced_existing"] is True
    response = client.post("/v1/query", json={"question": "networking content"})
    assert response.json()["citations"][0]["title"] == "New"


def test_blank_question_rejected(client):
    assert client.post("/v1/query", json={"question": "  "}).status_code == 422
