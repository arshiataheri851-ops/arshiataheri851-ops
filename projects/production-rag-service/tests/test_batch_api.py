def test_batch_ingestion_and_document_pagination(client):
    payload = {
        "documents": [
            {"document_id": "batch-a", "title": "Batch A", "text": "Alpha retrieval anchor."},
            {"document_id": "batch-b", "title": "Batch B", "text": "Beta retrieval anchor."},
            {"document_id": "batch-c", "title": "Batch C", "text": "Gamma retrieval anchor."},
        ]
    }
    response = client.post("/v1/documents/batch", json=payload)
    assert response.status_code == 201
    assert response.json()["accepted"] == 3

    first_page = client.get("/v1/documents?limit=2&offset=0")
    second_page = client.get("/v1/documents?limit=2&offset=2")
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1
    assert client.get("/health").json() == {"status": "ok", "service": "atlasrag"}


def test_batch_limit_is_validated(client):
    response = client.post("/v1/documents/batch", json={"documents": []})
    assert response.status_code == 422


def test_batch_rejects_duplicate_document_ids(client):
    response = client.post("/v1/documents/batch", json={"documents": [
        {"document_id": "duplicate", "title": "First", "text": "First document text."},
        {"document_id": "duplicate", "title": "Second", "text": "Second document text."},
    ]})
    assert response.status_code == 422
