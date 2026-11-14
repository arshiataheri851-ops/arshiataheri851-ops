# RoutePilot — Fleet & Delivery Operations MVP

RoutePilot is an executable fleet and delivery workflow MVP with a FastAPI + SQLite backend and browser dashboard. It supports vehicle records, submitted GPS telemetry, delivery creation/status, proof-of-delivery metadata and delivery-note preview.

## Included
- Responsive fleet operations dashboard
- Simulated vehicle positions and route paths (not connected to real GPS devices)
- Delivery table with status filtering and API-backed delivery creation
- Proof-of-delivery metadata capture and delivery-note preview
- Explicit sample-data and non-legal-document notices

## Run locally
Open `index.html` in a browser for the dashboard. Start the API from this folder with `docker compose up --build`; the API is bound to `127.0.0.1:8000`.

## CORS configuration
Copy `.env.example` to `.env` and set `ROUTEPILOT_CORS_ORIGINS` to the exact frontend origin(s), comma-separated. Do not use a wildcard. The default is for local development only. For public hosting, place the API behind a TLS reverse proxy and keep the container port private.

## Health checks
The API exposes `/health` for process liveness and `/ready` for database readiness. Docker uses the readiness endpoint for its container health check.

## Production architecture direction
A commercial deployment requires authenticated users, organization/tenant isolation, role permissions, PostgreSQL with migrations, tested backups and restore, HTTPS, monitoring, and operational runbooks. Real driver GPS requires a signed-in driver, vehicle assignment, explicit browser location permission and an active foreground web session. Browser web apps cannot guarantee continuous background GPS after the page is closed or suspended; reliable background tracking requires a suitable native app or dedicated device integration. Location access, consent, retention, role permissions, document templates and jurisdiction-specific requirements must be designed before production use.

## Important scope
This is an MVP, not a production-ready fleet system. Initial records are sample data. It does not connect to live vehicle hardware, store uploaded photographs or biometric signatures, issue legally valid transport documents, or include authentication/tenant isolation. Do not expose it publicly or enter real personal data until those controls are implemented and tested.

Built as an ERYNDEX portfolio project.

## Backend
See [backend setup](backend/README.md). Interactive API documentation is available at `/docs` while the local API is running.
