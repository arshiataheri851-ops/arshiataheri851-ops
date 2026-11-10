"""Transport-agnostic webhook routing, signing, and retry state management."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from typing import Callable
from urllib.parse import urlparse

Sender = Callable[[str, str, dict[str, str]], int]


@dataclass(frozen=True)
class Subscription:
    subscription_id: str
    event_type: str
    url: str
    secret: str


@dataclass
class Delivery:
    delivery_id: str
    event_id: str
    subscription_id: str
    event_type: str
    url: str
    body: str
    status: str = "queued"
    attempts: int = 0
    signature: str | None = None
    last_status_code: int | None = None
    last_error: str | None = None


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def create_signature(secret: str, body: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{body}".encode()
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: str, timestamp: int, signature: str) -> bool:
    expected = create_signature(secret, body, timestamp)
    return hmac.compare_digest(expected, signature)


class WebhookDispatcher:
    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._deliveries: dict[str, Delivery] = {}
        self._event_delivery_ids: dict[str, list[str]] = {}

    def register_subscription(
        self, subscription_id: str, event_type: str, url: str, secret: str
    ) -> Subscription:
        parsed = urlparse(url)
        if not subscription_id.strip() or not event_type.strip():
            raise ValueError("subscription_id and event_type are required")
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Webhook URL must be an absolute HTTPS URL")
        if len(secret) < 16:
            raise ValueError("Secret must contain at least 16 characters")
        if subscription_id in self._subscriptions:
            raise ValueError("Subscription already exists")
        item = Subscription(subscription_id, event_type, url, secret)
        self._subscriptions[subscription_id] = item
        return item

    def enqueue_event(
        self, event_id: str, event_type: str, payload: dict, timestamp: int
    ) -> list[str]:
        if not event_id.strip() or not event_type.strip():
            raise ValueError("event_id and event_type are required")
        if event_id in self._event_delivery_ids:
            return list(self._event_delivery_ids[event_id])

        event_body = canonical_json(
            {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_at": timestamp,
                "payload": payload,
            }
        )
        delivery_ids: list[str] = []
        for subscription in self._subscriptions.values():
            if subscription.event_type != event_type:
                continue
            delivery_id = f"{event_id}:{subscription.subscription_id}"
            self._deliveries[delivery_id] = Delivery(
                delivery_id=delivery_id,
                event_id=event_id,
                subscription_id=subscription.subscription_id,
                event_type=event_type,
                url=subscription.url,
                body=event_body,
            )
            delivery_ids.append(delivery_id)

        self._event_delivery_ids[event_id] = delivery_ids
        return list(delivery_ids)

    def dispatch(
        self,
        delivery_id: str,
        sender: Sender,
        timestamp: int,
        max_attempts: int = 3,
    ) -> Delivery:
        if max_attempts < 1 or max_attempts > 10:
            raise ValueError("max_attempts must be between 1 and 10")
        delivery = self._deliveries.get(delivery_id)
        if delivery is None:
            raise KeyError("Delivery not found")
        if delivery.status == "delivered" or delivery.status == "dead_letter":
            return delivery

        subscription = self._subscriptions[delivery.subscription_id]
        delivery.attempts += 1
        delivery.signature = create_signature(subscription.secret, delivery.body, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery": delivery.delivery_id,
            "X-Webhook-Timestamp": str(timestamp),
            "X-Webhook-Signature": delivery.signature,
        }
        try:
            status_code = sender(delivery.url, delivery.body, headers)
            delivery.last_status_code = int(status_code)
            if 200 <= delivery.last_status_code < 300:
                delivery.status = "delivered"
                delivery.last_error = None
            else:
                raise RuntimeError(f"Receiver returned HTTP {delivery.last_status_code}")
        except Exception as exc:
            delivery.last_error = f"{type(exc).__name__}: {exc}"
            delivery.status = "retry" if delivery.attempts < max_attempts else "dead_letter"
        return delivery

    def get_delivery(self, delivery_id: str) -> Delivery | None:
        return self._deliveries.get(delivery_id)

    def list_deliveries(self) -> list[dict]:
        return [asdict(item) for item in self._deliveries.values()]
