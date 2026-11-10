"""FastAPI endpoints for the ML feature store."""

import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.store import FeatureStore

FeatureType = Literal["integer", "number", "string", "boolean", "object"]


class FeatureGroupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    group_name: str = Field(min_length=1, max_length=100)
    feature_schema: dict[str, FeatureType] = Field(alias="schema")
    ttl_seconds: int | None = Field(default=None, ge=1)


class FeatureWriteRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=200)
    features: dict


class BatchGetRequest(BaseModel):
    entity_ids: list[str] = Field(min_length=1, max_length=500)


def create_app(store: FeatureStore | None = None) -> FastAPI:
    api = FastAPI(
        title="ML Feature Store",
        description="Typed feature writes, versioned values, and freshness-aware serving.",
        version="1.0.0",
    )
    api.state.store = store or FeatureStore(os.getenv("FEATURE_DB_PATH", ":memory:"))

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/feature-groups", status_code=201)
    def create_group(request: FeatureGroupRequest) -> dict:
        try:
            return api.state.store.create_group(
                request.group_name, request.feature_schema, request.ttl_seconds
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @api.put("/feature-groups/{group_name}/entities/{entity_id}")
    def write_features(group_name: str, entity_id: str, request: FeatureWriteRequest) -> dict:
        if entity_id != request.entity_id:
            raise HTTPException(status_code=400, detail="Path entity_id does not match request")
        try:
            return api.state.store.write(group_name, entity_id, request.features)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @api.get("/feature-groups/{group_name}/entities/{entity_id}")
    def get_features(group_name: str, entity_id: str) -> dict:
        try:
            return api.state.store.get(group_name, entity_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @api.post("/feature-groups/{group_name}/entities:batchGet")
    def batch_get(group_name: str, request: BatchGetRequest) -> list[dict]:
        try:
            return api.state.store.get_many(group_name, request.entity_ids)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return api


app = create_app()
