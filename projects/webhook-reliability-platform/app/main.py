"""RelayForge API: event intake, subscription routing, and delivery lifecycle."""

from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.dispatcher import Sender, WebhookDispatcher


class SubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    event_type: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=9, max_length=2_000)
    secret: str = Field(min_length=16, max_length=512)

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("url must be an absolute HTTPS URL without embedded credentials")
        return value


class EventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_.:-]+$")
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(max_length=100)
    timestamp: int = Field(gt=0)

    @field_validator("payload")
    @classmethod
    def limit_payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        import json

        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 256_000:
            raise ValueError("payload must be smaller than 256 KB")
        return value


def create_app(sender: Sender | None = None) -> FastAPI:
    api = FastAPI(
        title="RelayForge — Reliable Webhook Delivery Engine",
        description=(
            "Idempotent event routing, HMAC-SHA256 signing, bounded retries, "
            "and explicit dead-letter handling. The default mode performs no network calls."
        ),
        version="1.1.0",
    )
    api.state.dispatcher = WebhookDispatcher()
    api.state.sender = sender

    @api.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {"service": "relayforge", "version": api.version, "docs": "/docs"}

    @api.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok", "delivery_mode": "injected-transport-only"}

    @api.post("/subscriptions", status_code=status.HTTP_201_CREATED, tags=["subscriptions"])
    def create_subscription(request: SubscriptionRequest) -> dict[str, str]:
        try:
            item = api.state.dispatcher.register_subscription(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"subscription_id": item.subscription_id, "event_type": item.event_type}

    @api.get("/subscriptions", tags=["subscriptions"])
    def list_subscriptions() -> list[dict[str, str]]:
        return api.state.dispatcher.list_subscriptions()

    @api.delete("/subscriptions/{subscription_id}", tags=["subscriptions"])
    def delete_subscription(subscription_id: str) -> dict[str, bool | str]:
        try:
            deleted = api.state.dispatcher.remove_subscription(subscription_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="Subscription not found.")
        return {"subscription_id": subscription_id, "deleted": True}

    @api.post("/events", status_code=status.HTTP_202_ACCEPTED, tags=["events"])
    def create_event(request: EventRequest) -> dict[str, Any]:
        already_seen = api.state.dispatcher.was_event_seen(request.event_id)
        try:
            ids = api.state.dispatcher.enqueue_event(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "event_id": request.event_id,
            "delivery_ids": ids,
            "queued": len(ids),
            "idempotent_replay": already_seen,
        }

    @api.get("/deliveries", tags=["deliveries"])
    def list_deliveries(
        delivery_status: str | None = Query(default=None, alias="status"),
    ) -> list[dict[str, Any]]:
        if delivery_status is not None and delivery_status not in {
            "queued", "retry", "delivered", "dead_letter"
        }:
            raise HTTPException(status_code=422, detail="Unsupported delivery status.")
        return api.state.dispatcher.list_deliveries(delivery_status)

    @api.post("/deliveries/{delivery_id}/dispatch", tags=["deliveries"])
    def dispatch_delivery(
        delivery_id: str,
        timestamp: int = Query(gt=0),
        max_attempts: int = Query(default=3, ge=1, le=10),
    ) -> dict[str, Any]:
        if api.state.sender is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No delivery transport configured. Inject a sender into create_app(); "
                    "the default server never makes outbound network requests."
                ),
            )
        try:
            result = api.state.dispatcher.dispatch(
                delivery_id, api.state.sender, timestamp, max_attempts
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Delivery not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.__dict__

    return api


app = create_app()
