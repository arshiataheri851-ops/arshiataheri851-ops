from fastapi.testclient import TestClient

from app.main import create_app

PRODUCER_TOKEN = "p" * 40
OPERATOR_TOKEN = "o" * 40


def make_client(sender=None, *, authenticated=True):
    client = TestClient(create_app(
        sender=sender, api_token=PRODUCER_TOKEN, operator_token=OPERATOR_TOKEN
    ))
    if authenticated:
        client.headers.update({
            "X-RelayForge-API-Key": PRODUCER_TOKEN,
            "X-RelayForge-Operator-Key": OPERATOR_TOKEN,
        })
    return client


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
    client = make_client(sender=fake_sender)
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
    client = make_client()
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
    client = make_client()
    response = client.post("/deliveries/missing/dispatch?timestamp=1")
    assert response.status_code == 503


def test_secrets_are_never_returned_from_subscription_listing():
    client = make_client()
    client.post("/subscriptions", json=subscription_payload())
    response = client.get("/subscriptions")
    assert response.status_code == 200
    assert "secret" not in response.json()[0]


def test_subscription_cannot_be_removed_with_pending_deliveries():
    client = make_client()
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
    client = make_client()
    payload = subscription_payload()
    payload["url"] = "http://example.com/hook"
    assert client.post("/subscriptions", json=payload).status_code == 422


def test_management_and_delivery_routes_require_operator_token():
    client = make_client(authenticated=False)
    assert client.get("/subscriptions").status_code == 401
    assert client.get("/deliveries").status_code == 401
    assert client.post("/subscriptions", json=subscription_payload()).status_code == 401


def test_event_ingestion_requires_producer_token():
    client = make_client(authenticated=False)
    event_payload = {
        "event_id": "evt-auth", "event_type": "order.created",
        "payload": {}, "timestamp": 1700000000,
    }
    assert client.post("/events", json=event_payload).status_code == 401


def test_missing_auth_configuration_fails_closed():
    client = TestClient(create_app())
    assert client.post("/events", json={
        "event_id": "evt-unconfigured", "event_type": "order.created",
        "payload": {}, "timestamp": 1700000000,
    }).status_code == 503


def test_redrive_rejected_after_subscription_removal():
    client = make_client()
    assert client.post("/subscriptions", json=subscription_payload()).status_code == 201
    event = client.post("/events", json={
        "event_id": "evt-dead", "event_type": "order.created",
        "payload": {}, "timestamp": 1700000000,
    })
    delivery_id = event.json()["delivery_ids"][0]
    dispatcher = client.app.state.dispatcher
    dispatcher.dispatch(delivery_id, lambda *_: 503, timestamp=1700000001, max_attempts=1)
    assert dispatcher.get_delivery(delivery_id).status == "dead_letter"
    assert client.delete("/subscriptions/orders").status_code == 409
    assert client.post(f"/deliveries/{delivery_id}/redrive").status_code == 200
