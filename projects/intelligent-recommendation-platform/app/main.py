"""FastAPI endpoints for event ingestion and recommendations."""

import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.recommender import DEFAULT_CATALOG, RecommendationService
from app.store import EventStore


class EventRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    item_id: str = Field(min_length=1, max_length=120)
    event_type: Literal["view", "click", "purchase"]


def create_app(
    store: EventStore | None = None,
    catalog: list[dict] | None = None,
) -> FastAPI:
    event_store = store or EventStore(os.getenv("RECOMMENDER_DB_PATH", "recommendations.db"))
    service = RecommendationService(event_store, catalog or DEFAULT_CATALOG)
    api = FastAPI(
        title="Intelligent Recommendation Platform",
        description="Weighted implicit feedback, cold-start ranking, and explainable results.",
        version="1.0.0",
    )
    api.state.store = event_store
    api.state.service = service

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/catalog")
    def catalog_items() -> list[dict]:
        return service.catalog

    @api.post("/events", status_code=201)
    def create_event(request: EventRequest) -> dict:
        try:
            return service.record_event(
                request.user_id, request.item_id, request.event_type
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @api.get("/recommendations/{user_id}")
    def recommendations(
        user_id: str,
        limit: int = Query(default=5, ge=1, le=50),
    ) -> dict:
        try:
            return service.recommend(user_id, limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return api


app = create_app()
