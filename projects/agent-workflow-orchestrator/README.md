# Agent Workflow Orchestrator

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/agent-workflow-orchestrator.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/agent-workflow-orchestrator.yml)
An approval-aware, auditable workflow engine for coordinating multi-step work across specialist agents or external workers.

> This repository implements the orchestration control plane, not autonomous LLM agents. Workers are external adapters that claim tasks and submit results. The included engine is deterministic and testable without paid model APIs.

## What it demonstrates

- Directed acyclic graph (DAG) validation and dependency scheduling.
- Explicit task state machine: pending, ready, awaiting approval, running, succeeded, failed, and blocked.
- Human approval gates before sensitive downstream tasks become claimable.
- Bounded retries and downstream blocking after terminal failures.
- Persistent workflow state in SQLite.
- Append-only audit events recording actors, transitions, and result metadata.
- FastAPI endpoints suitable for worker adapters and operator tooling.

## Architecture

```text
Workflow definition
       |
       v
DAG validation ---> SQLite workflow store
       |                    |
       v                    v
Dependency scheduler <--- State machine
       |                    |
       +--> approval gate --+--> audit trail
       |
       +--> READY tasks --> external worker claims
                                  |
                         result / failure callback
                                  |
                         retry or downstream unlock
```

## Quick start

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Example workflow

Create a workflow with a research step followed by a human-approved review:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflows \\
  -H 'Content-Type: application/json' \\
  -d '{
    "workflow_id":"research-report",
    "title":"Research report",
    "tasks":[
      {"task_id":"research","role":"researcher","description":"Collect source material"},
      {"task_id":"review","role":"reviewer","description":"Review evidence",
       "depends_on":["research"],"requires_approval":true},
      {"task_id":"write","role":"writer","description":"Write the report",
       "depends_on":["review"]}
    ]
  }'
```

A worker claims a ready task, then submits its result:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflows/research-report/tasks/research/claim \\
  -H 'Content-Type: application/json' -d '{"actor":"research-worker-1"}'

curl -X POST http://127.0.0.1:8000/v1/workflows/research-report/tasks/research/complete \\
  -H 'Content-Type: application/json' \\
  -d '{"actor":"research-worker-1","result":{"source_count":8}}'
```

The review task then enters `awaiting_approval`. An operator approves it:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflows/research-report/tasks/review/approve \\
  -H 'Content-Type: application/json' -d '{"actor":"operator"}'
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/v1/workflows` | Validate and create a workflow |
| GET | `/v1/workflows/{id}` | Inspect workflow and task states |
| POST | `/v1/workflows/{id}/tasks/{task}/approve` | Approve a gated task |
| POST | `/v1/workflows/{id}/tasks/{task}/claim` | Claim a ready task |
| POST | `/v1/workflows/{id}/tasks/{task}/complete` | Submit task result |
| POST | `/v1/workflows/{id}/tasks/{task}/fail` | Report failure and schedule retry if allowed |
| GET | `/v1/workflows/{id}/audit` | Read workflow audit history |

## Tests

```bash
ruff check app tests
pytest -q
```

Tests cover cycle detection, unknown dependencies, state transitions, approval gates, retry exhaustion, downstream blocking, API behavior, and audit persistence.

## Security and production boundaries

- No model API keys or paid external services are required.
- Authentication and authorization are not included; deploy behind an authenticated gateway before exposing it to untrusted users.
- SQLite is intended for a single-instance demonstration. Multi-worker deployments need a transactional shared database and concurrency-safe task claiming.
- Worker identity is currently supplied by the caller; production deployments must derive it from verified credentials.
- Audit events are append-only through this API, but database-level tamper resistance and retention controls are deployment responsibilities.
- Task execution is deliberately outside the orchestrator process; this service tracks state and does not execute arbitrary code.
