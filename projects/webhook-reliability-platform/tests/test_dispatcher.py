import pytest

from app.dispatcher import WebhookDispatcher, create_signature, verify_signature


def configured_dispatcher():
    dispatcher = WebhookDispatcher()
    dispatcher.register_subscription(
        "billing", "invoice.paid", "https://hooks.example.com/billing", "s" * 32
    )
    return dispatcher


def test_idempotent_enqueue_and_event_routing():
    dispatcher = configured_dispatcher()
    first = dispatcher.enqueue_event("evt-1", "invoice.paid", {"amount": 50}, 100)
    second = dispatcher.enqueue_event("evt-1", "invoice.paid", {"amount": 50}, 100)
    assert first == second
    assert len(dispatcher.list_deliveries()) == 1


def test_hmac_signature_verification_and_tamper_detection():
    signature = create_signature("secret-value-long-enough", '{"ok":true}', 123)
    assert verify_signature("secret-value-long-enough", '{"ok":true}', 123, signature)
    assert not verify_signature("secret-value-long-enough", '{"ok":false}', 123, signature)


def test_retry_then_dead_letter_and_success():
    dispatcher = configured_dispatcher()
    delivery_id = dispatcher.enqueue_event("evt-2", "invoice.paid", {}, 100)[0]
    first = dispatcher.dispatch(delivery_id, lambda *_: 503, timestamp=101, max_attempts=2)
    assert first.status == "retry"
    second = dispatcher.dispatch(delivery_id, lambda *_: 503, timestamp=102, max_attempts=2)
    assert second.status == "dead_letter"
    assert second.attempts == 2

    next_id = dispatcher.enqueue_event("evt-3", "invoice.paid", {}, 100)[0]
    sent = dispatcher.dispatch(next_id, lambda *_: 204, timestamp=101)
    assert sent.status == "delivered"


def test_reject_insecure_subscription_url_and_short_secret():
    dispatcher = WebhookDispatcher()
    with pytest.raises(ValueError, match="HTTPS"):
        dispatcher.register_subscription("bad", "demo", "http://example.com/hook", "s" * 32)
    with pytest.raises(ValueError, match="16 characters"):
        dispatcher.register_subscription("short", "demo", "https://example.com/hook", "tiny")
