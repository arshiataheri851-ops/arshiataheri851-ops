# RoutePilot API

RoutePilot is a local fleet and delivery operations MVP built with FastAPI and SQLite.

## Run locally (Windows CMD)
```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```
Open the API at http://127.0.0.1:8000 and interactive docs at http://127.0.0.1:8000/docs.

## Run with Docker
From the RoutePilot project root: `docker compose up --build`.
The database is persisted in the `routepilot_data` Docker volume.

## Health and readiness
- `GET /health` — process liveness
- `GET /ready` — verifies that the configured SQLite database is reachable; returns HTTP 503 if it is unavailable

## Main workflows
- `GET /vehicles` — list fleet and latest submitted position
- `POST /vehicles` — add a vehicle
- `POST /vehicles/{vehicle_id}/positions` — record a submitted GPS coordinate
- `GET /vehicles/{vehicle_id}/positions?limit=100` — read position history
- `GET /deliveries` — list deliveries; optional `status` filter
- `POST /deliveries` — create a delivery and optionally associate a known vehicle
- `PATCH /deliveries/{delivery_id}/status` — update status; delivered requires proof first
- `POST /deliveries/{delivery_id}/proof` — record recipient/method/note and mark delivered
- `GET /deliveries/{delivery_id}/proofs` — list proof records
- `GET /deliveries/{delivery_id}/note` — structured document preview (not legally valid)

## Tests
From this folder:
```cmd
py -m pip install -r requirements.txt
py -m pytest -q
```

## Current limitations before customer deployment
This is an executable MVP, not a hardened commercial deployment. It has no user authentication, role permissions, tenant isolation, live GPS hardware/mobile driver app, uploaded photo/signature storage, notification service, database migrations, backups, or jurisdiction-approved transport documents. Do not expose it to the public internet or enter real customer personal data until these controls are implemented. Configure CORS for the exact production frontend origin before deployment.
