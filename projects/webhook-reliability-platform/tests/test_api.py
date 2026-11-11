from fastapi.testclient import TestClient

from app.main import create_app


def fake_sender(url: str, body: str, headers: dict[str, str]) -> int:
    assert url.startswith("https://")
    assert "X-Webhook-Signature" in headers
    assert '"event_id":"evt-api"' in body
    return 202


def subscription_payload() -> dict:
    return {
        "subscription_id": "orders",
        "event_type": "order.created",
        "url": "https://example.com/orders",
        "secret": "a-secure-secret-value",
    }


def test_event_ingestion_and_injected_dispatch():
    client = TestClient(create_app(sender=fake_sender))
    assert client.post("/subscriptions", json=subscription_payload()).status_code == 201

    event_payload = {
        "event_id": "evt-api",
        "event_type": "order.created",
        "payload": {"order_id": 42},
        "timestamp": 1700000000,
    }
    event = client.post("/events", json=event_payload)
    assert event.status_code == 202
    assert event.json()["idempotent_replay"] is False
    delivery_id = event.json()["delivery_ids"][0]

    replay = client.post("/events", json=event_payload)
    assert replay.status_code == 202
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["delivery_ids"] == [delivery_id]

    result = client.post(f"/deliveries/{delivery_id}/dispatch?timestamp=1700000001")
    assert result.status_code == 200
    assert result.json()["status"] == "delivered"


def test_reusing_event_id_with_different_payload_is_rejected():
    client = TestClient(create_app())
    client.post("/subscriptions", json=subscription_payload())
    first = {
        "event_id": "same-id",
        "event_type": "order.created",
        "payload": {"order_id": 1},
        "timestamp": 1700000000,
    }
    assert client.post("/events", json=first).status_code == 202
    first["payload"] = {"order_id": 2}
    assert client.post("/events", json=first).status_code == 409


def test_dispatch_without_transport_is_explicitly_unavailable():
    client = TestClient(create_app())
    response = client.post("/deliveries/missing/dispatch?timestamp=1")
    assert response.status_code == 503


def test_secrets_are_never_returned_from_subscription_listing():
    client = TestClient(create_app())
    client.post("/subscriptions", json=subscription_payload())
    response = client.get("/subscriptions")
    assert response.status_code == 200
    assert "secret" not in response.json()[0]


def test_subscription_cannot_be_removed_with_pending_deliveries():
    client = TestClient(create_app())
    client.post("/subscriptions", json=subscription_payload())
    client.post("/events", json={
        "event_id": "evt-pending",
        "event_type": "order.created",
        "payload": {},
        "timestamp": 1700000000,
    })
    response = client.delete("/subscriptions/orders")
    assert response.status_code == 409


def test_invalid_subscription_url_is_rejected():
    client = TestClient(create_app())
    payload = subscription_payload()
    payload["url"] = "http://example.com/hook"
    assert client.post("/subscriptions", json=payload).status_code == 422
