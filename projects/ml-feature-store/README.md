# ML Feature Store

A compact online feature store for machine-learning services. It manages feature-group schemas, validates entity feature writes, versions updates, serves single or batch lookups, and reports feature freshness using configurable TTLs.

## Features

- Typed feature-group registry
- SQLite-backed entity feature values
- Schema enforcement and undeclared-feature rejection
- Per-feature version counters
- Single and batch retrieval
- TTL-based freshness metadata
- FastAPI, unit/API tests, and Python 3.11/3.13 CI

## Quick start

```bash
python -m venv .venv
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The default database is in-memory. Set `FEATURE_DB_PATH` to a filesystem path for persistence.

## API

- `GET /health`
- `POST /feature-groups`
- `PUT /feature-groups/{group_name}/entities/{entity_id}`
- `GET /feature-groups/{group_name}/entities/{entity_id}`
- `POST /feature-groups/{group_name}/entities:batchGet`

## Limitations

This is a single-process reference service using SQLite and a synchronous connection. It demonstrates schema enforcement, feature versioning, and serving freshness—not distributed consistency or high-throughput serving. A production system would add authentication, authorization, migrations, connection pooling, point-in-time-correct offline storage, monitoring, and a distributed cache/database. No model or external data provider is bundled.
