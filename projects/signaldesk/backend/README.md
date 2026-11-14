# SignalDesk API

SignalDesk is a local service-desk MVP built with FastAPI and SQLite. Ticket assignment and status changes persist, SLA risk is calculated from each ticket's due date, and workflow events are retained in an audit-history table.

## Run locally (Windows CMD)
```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --port 8001
```
Open http://127.0.0.1:8001 and interactive docs at http://127.0.0.1:8001/docs.

## Run with Docker
From the SignalDesk project root: `docker compose up --build`.
The database is persisted in the `signaldesk_data` Docker volume.

## Health and readiness
- `GET /health` — process liveness
- `GET /ready` — verifies that the configured SQLite database is reachable; returns HTTP 503 if it is unavailable

## Main workflows
- `GET /tickets` — list and filter by status, queue, priority, SLA risk and text query
- `POST /tickets` — create a ticket with a due date
- `PATCH /tickets/{ticket_id}/assign` — assign an open ticket
- `PATCH /tickets/{ticket_id}/status` — open, in progress or resolved
- `GET /tickets/{ticket_id}/events` — audit history for a ticket
- `GET /analytics/summary` — current queue/SLA summary

SLA risk is a transparent rule: a ticket is at risk when it is not resolved and has 30 minutes or less remaining. Priority score is a deterministic weighted rule, not an AI prediction.

## Tests
From this folder:
```cmd
py -m pip install -r requirements.txt
py -m pytest -q
```

## Current limitations before customer deployment
This is an executable MVP, not a hardened commercial deployment. It has no user authentication, role permissions, tenant isolation, email intake, outbound notifications, configurable SLA calendars, attachments, database migrations, backups, or external integrations. Do not expose it to the public internet or store real customer personal data until these controls are implemented. Configure CORS for the exact production frontend origin before deployment.
