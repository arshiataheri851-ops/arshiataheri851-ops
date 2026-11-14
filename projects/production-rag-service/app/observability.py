"""Low-cardinality Prometheus metrics and privacy-preserving audit events."""

import hashlib
import json
import logging
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

REGISTRY = CollectorRegistry()
HTTP_REQUESTS = Counter(
    "atlasrag_http_requests_total",
    "HTTP requests handled by AtlasRAG.",
    ("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_LATENCY = Histogram(
    "atlasrag_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    registry=REGISTRY,
)
AUDIT_LOGGER = logging.getLogger("atlasrag.audit")
AUDIT_LOGGER.setLevel(logging.INFO)
if not AUDIT_LOGGER.handlers:
    AUDIT_LOGGER.addHandler(logging.StreamHandler())


def instrument_api(api: FastAPI) -> None:
    @api.middleware("http")
    async def collect_request_metrics(request: Request, call_next: Any):
        started = perf_counter()
        method = request.method
        try:
            response = await call_next(request)
        except Exception:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            HTTP_REQUESTS.labels(method, route, "500").inc()
            HTTP_LATENCY.labels(method, route).observe(perf_counter() - started)
            raise
        route = getattr(request.scope.get("route"), "path", "unmatched")
        HTTP_REQUESTS.labels(method, route, str(response.status_code)).inc()
        HTTP_LATENCY.labels(method, route).observe(perf_counter() - started)
        return response


def audit_event(
    event: str,
    tenant_id: str,
    *,
    document_id: str | None = None,
    item_count: int | None = None,
    outcome: str = "success",
) -> None:
    """Log metadata only; never include keys, queries, document text, or source URLs."""
    record: dict[str, str | int] = {
        "event": event,
        "tenant_id": tenant_id,
        "outcome": outcome,
    }
    if document_id is not None:
        record["document_ref"] = hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:16]
    if item_count is not None:
        record["item_count"] = item_count
    AUDIT_LOGGER.info(json.dumps(record, separators=(",", ":"), ensure_ascii=True))


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
