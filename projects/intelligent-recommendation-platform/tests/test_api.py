from fastapi.testclient import TestClient

from app.main import create_app
from app.store import EventStore


def test_event_ingestion_and_personalized_recommendations():
    client = TestClient(create_app(EventStore(clock=lambda: 100.0)))

    recorded = client.post(
        "/events",
        json={
            "user_id": "student-7",
            "item_id": "course-python",
            "event_type": "purchase",
        },
    )
    assert recorded.status_code == 201

    response = client.get("/recommendations/student-7?limit=3")
    assert response.status_code == 200
    assert response.json()["strategy"] == "personalized_implicit_feedback"
    assert all(
        item["item_id"] != "course-python"
        for item in response.json()["recommendations"]
    )


def test_unknown_catalog_item_returns_404():
    client = TestClient(create_app(EventStore()))
    response = client.post(
        "/events",
        json={
            "user_id": "student-7",
            "item_id": "not-in-catalog",
            "event_type": "view",
        },
    )
    assert response.status_code == 404


def test_catalog_endpoint_and_limit_validation():
    client = TestClient(create_app(EventStore()))
    catalog = client.get("/catalog")
    assert catalog.status_code == 200
    assert len(catalog.json()) >= 5

    invalid = client.get("/recommendations/student-7?limit=100")
    assert invalid.status_code == 422
