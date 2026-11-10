"""FastAPI endpoints for the webhook reliability core."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.dispatcher import Sender, WebhookDispatcher


class SubscriptionRequest(BaseModel):
    subscription_id: str = Field(min_length=1, max_length=80)
    event_type: str = Field(min_length=1, max_length=120)
    url: str
    secret: str = Field(min_length=16, max_length=512)


class EventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict
    timestamp: int


def create_app(sender: Sender | None = None) -> FastAPI:
    api = FastAPI(
        title="Webhook Reliability Platform",
        description="Idempotent event routing, signed deliveries, and bounded retries.",
        version="1.0.0",
    )
    api.state.dispatcher = WebhookDispatcher()
    api.state.sender = sender

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/subscriptions", status_code=201)
    def create_subscription(request: SubscriptionRequest) -> dict:
        try:
            item = api.state.dispatcher.register_subscription(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"subscription_id": item.subscription_id, "event_type": item.event_type}

    @api.post("/events", status_code=202)
    def create_event(request: EventRequest) -> dict:
        try:
            ids = api.state.dispatcher.enqueue_event(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"event_id": request.event_id, "delivery_ids": ids, "queued": len(ids)}

    @api.get("/deliveries")
    def list_deliveries() -> list[dict]:
        return api.state.dispatcher.list_deliveries()

    @api.post("/deliveries/{delivery_id}/dispatch")
    def dispatch_delivery(delivery_id: str, timestamp: int, max_attempts: int = 3) -> dict:
        if api.state.sender is None:
            raise HTTPException(
                status_code=503,
                detail="No delivery transport configured; inject a sender into create_app().",
            )
        try:
            result = api.state.dispatcher.dispatch(
                delivery_id, api.state.sender, timestamp, max_attempts
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.__dict__

    return api


app = create_app()
