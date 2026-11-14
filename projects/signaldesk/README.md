# SignalDesk — Service Operations Intelligence MVP

SignalDesk is an executable service-desk MVP with a FastAPI + SQLite backend and browser dashboard for creating, assigning, prioritizing and tracking support tickets.

## Included
- Sample operations overview with queue metrics
- Searchable request queue
- Priority and SLA-risk filters
- API-backed assignment, status changes and per-ticket audit history
- Queue distribution visualization
- Transparent rule-based prioritization explanation

## Run locally
Open `index.html` in a modern browser. Start the API from this folder with `docker compose up --build`; the API is bound to `127.0.0.1:8001`.

## CORS configuration
Copy `.env.example` to `.env` and set `SIGNALDESK_CORS_ORIGINS` to the exact frontend origin(s), comma-separated. Do not use a wildcard. The default is for local development only. For public hosting, place the API behind a TLS reverse proxy and keep the container port private.

## Health checks
The API exposes `/health` for process liveness and `/ready` for database readiness. Docker uses the readiness endpoint for its container health check.

## Production requirements
A commercial deployment requires authenticated users, organization/tenant isolation, role permissions, PostgreSQL with migrations, tested backups and restore, HTTPS, monitoring, and operational runbooks. Email intake and outbound notifications require a configured provider, verified sender domain, credentials stored outside source control, retry handling and delivery logs. Any AI-assisted triage must be separately evaluated, explainable, permission-aware and subject to human review.

## Important scope
This is an MVP, not a production-ready service desk. Initial records are illustrative. New tickets, assignments and status changes persist in SQLite when the API is running. SLA risk and priority are transparent deterministic rules, not AI predictions. Authentication, roles, tenant isolation, email intake and notifications are not yet implemented. Do not expose it publicly or store real customer data before these controls are added and tested.

Built as an ERYNDEX portfolio project.

## Backend
See [backend setup](backend/README.md). Interactive API documentation is available at `/docs` while the local API is running.
