# Workflow Orchestration Engine

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/advanced-engineering-projects.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/advanced-engineering-projects.yml)
A small, inspectable DAG workflow runner built with Python and FastAPI. It validates dependencies, detects cycles, executes steps in topological order, records step outcomes, retries failed actions, and skips downstream steps when prerequisites fail.

## Features

- Directed acyclic graph validation with unknown-dependency and cycle detection
- Deterministic topological execution
- Pluggable action registry (built-in sum, multiply, concatenate, and dependency-copy actions)
- Per-step status, attempt count, output, and error reporting
- Configurable retry limit and explicit skipped-step behavior
- FastAPI endpoints for workflow validation and execution
- Unit/API tests and Python 3.11/3.13 CI

## Quick start

```bash
python -m venv .venv
# Activate the environment using your platform's normal method.
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open `/docs` for the interactive API documentation.

## Example request

```json
{
  "steps": [
    {"name": "total", "action": "sum", "params": {"values": [10, 20, 12]}},
    {"name": "label", "action": "concat", "depends_on": ["total"], "params": {"values": ["Total: ", "42"]}},
    {"name": "result", "action": "copy_dependency", "depends_on": ["total"], "params": {"dependency": "total"}}
  ],
  "max_attempts": 2
}
```

## API

- `GET /health`
- `POST /workflows/validate`
- `POST /workflows/execute`

## Design notes and limitations

This is a synchronous, single-process reference implementation. Execution state is held in memory and retries are immediate; it is not a distributed scheduler and does not promise durable execution across restarts. A production evolution would add persistent state, worker leases, delayed retry scheduling, cancellation, resource limits, and distributed tracing. No external LLM or paid service is required.
