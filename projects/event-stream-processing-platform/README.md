# Event Stream Processing Platform

A compact, dependency-light reference implementation of a reliable event ingestion pipeline. It demonstrates schema validation, idempotent writes, a dead-letter queue, durable storage, and deterministic windowed aggregation that can be rebuilt from the event log.

## Features

- Validates event identifiers, event types, timezone-aware ISO-8601 timestamps, and numeric values.
- Uses a SQLite primary key to make ingestion idempotent.
- Stores malformed events and rejection reasons in a dead-letter table.
- Persists accepted events independently of aggregate materializations.
- Rebuilds fixed-width time-window aggregates from the event log, supporting deterministic replay.
- Uses only the Python standard library at runtime.

## Quick start

```bash
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Example

```python
from app.pipeline import EventPipeline

pipeline = EventPipeline("events.db")
result = pipeline.ingest({
    "event_id": "order-1001",
    "event_type": "order_created",
    "occurred_at": "2026-11-10T10:01:15Z",
    "value": 49.90,
})
print(result)
pipeline.rebuild_aggregates(window_minutes=5)
print(pipeline.get_aggregates())
```

## Data model

- `events`: accepted event records; `event_id` is the idempotency key.
- `dead_letters`: rejected payloads and validation reasons for later inspection.
- `aggregates`: derived window summaries. Rebuilding clears and deterministically recreates this table from accepted events.

## Design notes and limitations

This is an educational single-process reference, not a distributed streaming broker. It does not claim Kafka-like throughput, exactly-once delivery across external systems, late-event watermark management, or multi-node coordination. SQLite transactions and a unique event key provide local durability and duplicate suppression. Production deployments would typically add broker offsets, schema versioning, bounded retention, metrics, access controls, and explicit late-event policies.
