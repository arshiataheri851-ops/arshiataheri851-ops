from fastapi.testclient import TestClient

from app.main import create_app


def fake_sender(url: str, body: str, headers: dict[str, str]) -> int:
    assert url.startswith("https://")
    assert "X-Webhook-Signature" in headers
    assert '"event_id":"evt-api"' in body
    return 202


def test_event_ingestion_and_injected_dispatch():
    client = TestClient(create_app(sender=fake_sender))
    subscription = client.post(
        "/subscriptions",
        json={
            "subscription_id": "orders",
            "event_type": "order.created",
            "url": "https://example.com/orders",
            "secret": "a-secure-secret-value",
        },
    )
    assert subscription.status_code == 201

    event = client.post(
        "/events",
        json={
            "event_id": "evt-api",
            "event_type": "order.created",
            "payload": {"order_id": 42},
            "timestamp": 1700000000,
        },
    )
    assert event.status_code == 202
    delivery_id = event.json()["delivery_ids"][0]
    result = client.post(f"/deliveries/{delivery_id}/dispatch?timestamp=1700000001")
    assert result.status_code == 200
    assert result.json()["status"] == "delivered"


def test_dispatch_without_transport_is_explicitly_unavailable():
    client = TestClient(create_app())
    response = client.post("/deliveries/missing/dispatch?timestamp=1")
    assert response.status_code == 503
