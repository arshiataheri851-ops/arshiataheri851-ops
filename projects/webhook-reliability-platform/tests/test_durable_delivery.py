import time

from fastapi.testclient import TestClient

import app.sender as sender_module
from app.dispatcher import WebhookDispatcher
from app.main import create_app
from app.sender import HttpxWebhookSender

PRODUCER_TOKEN = "p" * 40
OPERATOR_TOKEN = "o" * 40
AUTH_HEADERS = {
    "X-RelayForge-API-Key": PRODUCER_TOKEN,
    "X-RelayForge-Operator-Key": OPERATOR_TOKEN,
}


def payload(event_id="persisted-event"):
    return {
        "event_id": event_id,
        "event_type": "invoice.paid",
        "payload": {"invoice_id": "inv-123"},
        "timestamp": 1700000000,
    }


def add_subscription(dispatcher):
    dispatcher.register_subscription(
        "billing", "invoice.paid", "https://hooks.example.com/billing", "s" * 32
    )


def test_event_and_delivery_survive_dispatcher_restart(tmp_path):
    database = str(tmp_path / "relayforge.sqlite3")
    first = WebhookDispatcher(database)
    add_subscription(first)
    ids = first.enqueue_event(**payload())
    assert len(ids) == 1

    restarted = WebhookDispatcher(database)
    assert restarted.was_event_seen("persisted-event")
    assert restarted.get_delivery(ids[0]).status == "queued"
    assert restarted.list_subscriptions()[0]["subscription_id"] == "billing"


def test_retry_is_scheduled_then_delivered_by_due_worker(tmp_path):
    dispatcher = WebhookDispatcher(str(tmp_path / "retry.sqlite3"))
    add_subscription(dispatcher)
    delivery_id = dispatcher.enqueue_event(**payload("retry-event"))[0]
    calls = []

    def sender(*_):
        calls.append(time.time())
        return 503 if len(calls) == 1 else 204

    first = dispatcher.dispatch(
        delivery_id, sender, int(time.time()), max_attempts=3,
        base_delay_seconds=0.01, max_delay_seconds=0.01,
    )
    assert first.status == "retry"
    time.sleep(0.02)
    assert dispatcher.dispatch_due(
        sender, max_attempts=3, base_delay_seconds=0.01
    )[0].status == "delivered"
    final = dispatcher.get_delivery(delivery_id)
    assert final.status == "delivered"
    assert final.attempts == 2


def test_background_worker_sends_and_persists_delivery(tmp_path):
    calls = []

    def sender(url, body, headers):
        calls.append(headers["X-Webhook-Delivery"])
        return 202

    app = create_app(
        sender=sender,
        database_path=str(tmp_path / "worker.sqlite3"),
        enable_worker=True,
        api_token=PRODUCER_TOKEN,
        operator_token=OPERATOR_TOKEN,
        poll_interval_seconds=0.01,
        max_attempts=3,
    )
    with TestClient(app, headers=AUTH_HEADERS) as client:
        assert client.post("/subscriptions", json={
            "subscription_id": "billing",
            "event_type": "invoice.paid",
            "url": "https://hooks.example.com/billing",
            "secret": "s" * 32,
        }).status_code == 201
        event = client.post("/events", json=payload("worker-event")).json()
        delivery_id = event["delivery_ids"][0]
        deadline = time.time() + 2
        state = "queued"
        while time.time() < deadline:
            state = client.get(f"/deliveries/{delivery_id}").json()["status"]
            if state == "delivered":
                break
            time.sleep(0.01)
        assert state == "delivered"
        assert calls == [delivery_id]


def test_worker_requires_a_real_sender():
    try:
        create_app(enable_worker=True)
    except ValueError as exc:
        assert "sender" in str(exc)
    else:
        raise AssertionError("worker must not start without a configured sender")


def _dns_record(address: str):
    import socket

    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)
    return (family, socket.SOCK_STREAM, 6, "", sockaddr)


def test_http_sender_pins_connection_to_validated_dns_address(monkeypatch):
    observed = {}

    class FakeResponse:
        status = 202

    class FakeConnection:
        def __init__(self, hostname, port, address, timeout_seconds):
            observed.update(hostname=hostname, port=port, address=address, timeout=timeout_seconds)

        def request(self, method, target, body, headers):
            observed.update(method=method, target=target, body=body, headers=headers)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            observed["closed"] = True

    monkeypatch.setattr(sender_module.socket, "getaddrinfo", lambda *a, **k: [
        _dns_record("93.184.216.34")
    ])
    monkeypatch.setattr(sender_module, "_PinnedHTTPSConnection", FakeConnection)
    sender = HttpxWebhookSender({"hooks.example.com"})
    result = sender(
        "https://hooks.example.com/orders?region=eu",
        '{"order":42}',
        {"X-Webhook-Signature": "sig"},
    )

    assert result == 202
    assert observed["hostname"] == "hooks.example.com"
    assert observed["port"] == 443
    assert observed["address"] == "93.184.216.34"
    assert observed["target"] == "/orders?region=eu"
    assert observed["body"] == b'{"order":42}'
    assert observed["headers"]["Connection"] == "close"
    assert observed["closed"] is True


def test_http_sender_rejects_mixed_public_and_private_dns_answers(monkeypatch):
    monkeypatch.setattr(sender_module.socket, "getaddrinfo", lambda *a, **k: [
        _dns_record("93.184.216.34"),
        _dns_record("10.0.0.8"),
    ])

    def must_not_connect(*args, **kwargs):
        raise AssertionError("connection must not be attempted for mixed DNS answers")

    monkeypatch.setattr(sender_module, "_PinnedHTTPSConnection", must_not_connect)
    sender = HttpxWebhookSender({"hooks.example.com"})
    try:
        try:
            sender("https://hooks.example.com/hook", "{}", {})
        except ValueError as exc:
            assert "non-public" in str(exc)
        else:
            raise AssertionError("private DNS answer must be rejected")
    finally:
        sender.close()


def test_http_sender_rejects_non_allowlisted_host_before_dns(monkeypatch):
    def dns_must_not_run(*args, **kwargs):
        raise AssertionError("DNS must not run for a non-allowlisted host")

    monkeypatch.setattr(sender_module.socket, "getaddrinfo", dns_must_not_run)
    sender = HttpxWebhookSender({"hooks.example.com"})
    try:
        try:
            sender("https://other.example.com/hook", "{}", {})
        except ValueError as exc:
            assert "allowlisted" in str(exc)
        else:
            raise AssertionError("unapproved hostname should be rejected")
    finally:
        sender.close()


def test_http_sender_rejects_nonstandard_https_port():
    sender = HttpxWebhookSender({"hooks.example.com"})
    try:
        try:
            sender("https://hooks.example.com:8443/hook", "{}", {})
        except ValueError as exc:
            assert "port 443" in str(exc)
        else:
            raise AssertionError("non-standard ports must be rejected")
    finally:
        sender.close()


def test_dead_letter_can_be_redriven_by_operator():
    app = create_app(sender=lambda *_: 503, api_token=PRODUCER_TOKEN, operator_token=OPERATOR_TOKEN)
    with TestClient(app, headers=AUTH_HEADERS) as client:
        client.post("/subscriptions", json={
            "subscription_id": "billing",
            "event_type": "invoice.paid",
            "url": "https://hooks.example.com/billing",
            "secret": "s" * 32,
        })
        event = client.post("/events", json=payload("dead-letter-event")).json()
        delivery_id = event["delivery_ids"][0]
        failed = client.post(
            f"/deliveries/{delivery_id}/dispatch?timestamp=1700000001&max_attempts=1"
        )
        assert failed.json()["status"] == "dead_letter"

        redriven = client.post(f"/deliveries/{delivery_id}/redrive")
        assert redriven.status_code == 200
        assert redriven.json()["status"] == "queued"
        assert redriven.json()["attempts"] == 0


def test_non_dead_letter_delivery_cannot_be_redriven():
    app = create_app(sender=lambda *_: 204, api_token=PRODUCER_TOKEN, operator_token=OPERATOR_TOKEN)
    with TestClient(app, headers=AUTH_HEADERS) as client:
        client.post("/subscriptions", json={
            "subscription_id": "billing",
            "event_type": "invoice.paid",
            "url": "https://hooks.example.com/billing",
            "secret": "s" * 32,
        })
        event = client.post("/events", json=payload("queued-event")).json()
        delivery_id = event["delivery_ids"][0]
        response = client.post(f"/deliveries/{delivery_id}/redrive")
        assert response.status_code == 409
