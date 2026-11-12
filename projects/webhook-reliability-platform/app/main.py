"""RelayForge API with durable outbox and optional background delivery worker."""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.dispatcher import Sender, WebhookDispatcher
from app.sender import HttpxWebhookSender


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


def _worker_enabled() -> bool:
    return os.getenv("RELAYFORGE_ENABLE_WORKER", "false").lower() in {"1", "true", "yes"}


def _allowed_hosts() -> set[str]:
    return {
        host.strip().lower()
        for host in os.getenv("RELAYFORGE_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }


def create_app(
    sender: Sender | None = None,
    database_path: str = ":memory:",
    enable_worker: bool = False,
    poll_interval_seconds: float = 1.0,
    max_attempts: int = 5,
    retry_base_delay_seconds: float = 2.0,
) -> FastAPI:
    if enable_worker and sender is None:
        raise ValueError("Background delivery requires a configured sender")

    dispatcher = WebhookDispatcher(database_path)

    async def worker_loop() -> None:
        while True:
            try:
                await asyncio.to_thread(
                    dispatcher.dispatch_due, sender, max_attempts, 50,
                    retry_base_delay_seconds,
                )
            except Exception:
                # Keep the worker alive; operational logs/metrics should alert on repeated failures.
                await asyncio.sleep(max(poll_interval_seconds, 1.0))
                continue
            await asyncio.sleep(poll_interval_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(worker_loop()) if enable_worker else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            close = getattr(sender, "close", None)
            if callable(close):
                close()

    api = FastAPI(
        title="RelayForge — Reliable Webhook Delivery Engine",
        description=(
            "Durable SQLite outbox, allowlisted HTTP transport, HMAC-SHA256 signing, "
            "automatic exponential-backoff retries, and dead-letter handling. "
            "Delivery semantics are at-least-once; receivers should deduplicate by delivery ID."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )
    api.state.dispatcher = dispatcher
    api.state.sender = sender
    api.state.worker_enabled = enable_worker

    @api.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {"service": "relayforge", "version": api.version, "docs": "/docs"}

    @api.get("/health", tags=["service"])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "storage": "sqlite",
            "delivery_mode": "automatic" if enable_worker else (
                "manual" if sender is not None else "disabled"
            ),
            "pending_deliveries": dispatcher.count_pending(),
            "total_deliveries": dispatcher.count_deliveries(),
        }

    @api.post("/subscriptions", status_code=status.HTTP_201_CREATED, tags=["subscriptions"])
    def create_subscription(request: SubscriptionRequest) -> dict[str, str]:
        try:
            item = dispatcher.register_subscription(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"subscription_id": item.subscription_id, "event_type": item.event_type}

    @api.get("/subscriptions", tags=["subscriptions"])
    def list_subscriptions() -> list[dict[str, str]]:
        return dispatcher.list_subscriptions()

    @api.delete("/subscriptions/{subscription_id}", tags=["subscriptions"])
    def delete_subscription(subscription_id: str) -> dict[str, bool | str]:
        try:
            deleted = dispatcher.remove_subscription(subscription_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="Subscription not found.")
        return {"subscription_id": subscription_id, "deleted": True}

    @api.post("/events", status_code=status.HTTP_202_ACCEPTED, tags=["events"])
    def create_event(request: EventRequest) -> dict[str, Any]:
        already_seen = dispatcher.was_event_seen(request.event_id)
        try:
            ids = dispatcher.enqueue_event(**request.model_dump())
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
        delivery_status: Annotated[str | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[dict[str, Any]]:
        if delivery_status is not None and delivery_status not in {
            "queued", "sending", "retry", "delivered", "dead_letter"
        }:
            raise HTTPException(status_code=422, detail="Unsupported delivery status.")
        return dispatcher.list_deliveries(delivery_status, limit)

    @api.get("/deliveries/{delivery_id}", tags=["deliveries"])
    def get_delivery(delivery_id: str) -> dict[str, Any]:
        item = dispatcher.get_delivery(delivery_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Delivery not found.")
        return item.__dict__

    @api.post("/deliveries/{delivery_id}/redrive", tags=["deliveries"])
    def redrive_delivery(delivery_id: str) -> dict[str, Any]:
        current = dispatcher.get_delivery(delivery_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Delivery not found.")
        if current.status != "dead_letter":
            raise HTTPException(
                status_code=409,
                detail="Only dead-letter deliveries can be redriven.",
            )
        item = dispatcher.redrive_delivery(delivery_id)
        return item.__dict__

    @api.post("/deliveries/{delivery_id}/dispatch", tags=["deliveries"])
    def dispatch_delivery(
        delivery_id: str,
        timestamp: Annotated[int, Query(gt=0)] | None = None,
        max_attempts: Annotated[int, Query(ge=1, le=10)] = 5,
    ) -> dict[str, Any]:
        if api.state.sender is None:
            raise HTTPException(
                status_code=503,
                detail="No transport configured. Set RELAYFORGE_ALLOWED_HOSTS or inject a sender.",
            )
        try:
            result = dispatcher.dispatch(
                delivery_id, api.state.sender, timestamp or int(time.time()), max_attempts
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Delivery not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.__dict__

    return api


def _production_sender() -> HttpxWebhookSender | None:
    hosts = _allowed_hosts()
    return HttpxWebhookSender(hosts) if hosts else None


app = create_app(
    sender=_production_sender(),
    database_path=os.getenv("RELAYFORGE_DATABASE_PATH", "data/relayforge.sqlite3"),
    enable_worker=_worker_enabled(),
    max_attempts=int(os.getenv("RELAYFORGE_MAX_ATTEMPTS", "5")),
    retry_base_delay_seconds=float(os.getenv("RELAYFORGE_RETRY_BASE_DELAY_SECONDS", "2")),
)
