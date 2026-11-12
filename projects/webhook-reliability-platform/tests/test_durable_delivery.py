import time

from fastapi.testclient import TestClient

from app.dispatcher import WebhookDispatcher
from app.main import create_app
from app.sender import HttpxWebhookSender


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
        poll_interval_seconds=0.01,
        max_attempts=3,
    )
    with TestClient(app) as client:
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


def test_http_sender_rejects_non_allowlisted_host_before_network_access():
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
