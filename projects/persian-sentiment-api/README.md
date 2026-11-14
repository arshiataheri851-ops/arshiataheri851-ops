# FarsiPulse — Persian Sentiment Intelligence API


🌐 **Live product website:** [Open FarsiPulse](https://farsipulse.onrender.com)

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)
[![Real inference](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/farsipulse-real-inference.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/farsipulse-real-inference.yml)
[![Model evaluation](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/farsipulse-evaluation.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/farsipulse-evaluation.yml)

FarsiPulse is a typed REST service for binary Persian review sentiment inference. It combines conservative Persian normalization, FastAPI request validation, lazy Hugging Face model loading, bounded batch inference, and reproducible evaluation.

## What is implemented

- Single-text and batch prediction endpoints (batch capped at 32 items).
- Pydantic request/response contracts and blank-input rejection.
- Persian Arabic-letter normalization without stripping meaningful ZWNJ characters.
- Lazy model initialization with thread-safe first load.
- Pinned Hugging Face model revision.
- Configurable inference batch size and CPU thread count to limit memory use and CPU oversubscription.
- Constant-time API-key validation for inference routes; protected deployments can require the key at startup with `SENTIMENT_REQUIRE_API_KEY=true`.
- Non-root CPU-only Docker image, health endpoint, evaluation workflow, and automated tests.

## Architecture

```text
HTTP Client
    |
    v
FastAPI Router + API-key dependency + Pydantic Contracts
    |
    v
Persian Text Normalizer
    |
    v
Thread-safe Hugging Face Adapter (lazy load + bounded batches)
    |
    v
Positive / Negative scores + model provenance
```

## Run locally

Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs. The API starts without model weights; the first prediction returns a clear 503 until inference dependencies are installed.

For real model inference:

```bash
python -m pip install -e ".[inference]"
```

The first prediction downloads the pinned model revision from Hugging Face and may take several minutes. Set `SENTIMENT_MODEL_ID` and `SENTIMENT_MODEL_REVISION` only when intentionally switching models.

## API examples

Single prediction:

```bash
curl -X POST http://127.0.0.1:8000/v1/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text":"کیفیت غذا عالی بود و خیلی راضی بودم"}'
```

If `SENTIMENT_API_KEY` is configured, add `-H "X-API-Key: YOUR_SECRET"` to inference requests. Local development may leave the key optional. Set `SENTIMENT_REQUIRE_API_KEY=true` for protected deployments; the service then refuses to start if a valid key is missing. Health and service metadata endpoints remain public for platform health checks.

Batch prediction:

```bash
curl -X POST http://127.0.0.1:8000/v1/sentiment/batch \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"خیلی خوب بود"},{"text":"اصلاً راضی نبودم"}]}'
```

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Health and model-load state |
| POST | `/v1/sentiment` | One prediction |
| POST | `/v1/sentiment/batch` | Batch prediction |

The model returns a binary `positive` / `negative` label. Scores are raw model outputs, not calibrated probabilities or guarantees.

## Performance controls

- `SENTIMENT_INFERENCE_BATCH_SIZE`: transformer pipeline batch size (default 16; valid 1–32).
- `SENTIMENT_CPU_THREADS`: PyTorch intra-op CPU thread count (default 2; valid 1–16).
- `SENTIMENT_MAX_SEQUENCE_LENGTH`: tokenizer truncation limit (default 512).

The Docker image uses one Uvicorn worker because each worker loads its own model copy. Tune these values only after measuring latency and peak memory on the target host. Reducing sequence length can change model quality and should be evaluated first.

## Tests and lint

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Fast tests use a deterministic fake predictor and do not download model weights. A separate real-inference workflow downloads the pinned model and verifies single and batch API calls.

## Reproducible evaluation

```bash
python -m pip install -e ".[inference,evaluation,dev]"
python scripts/evaluate.py --batch-size 8 --output artifacts/report.json
```

The script evaluates the pinned model on the upstream dataset's fixed `test.csv` split and records accuracy, balanced accuracy, per-class precision/recall/F1, confusion matrix, throughput, batch latency, and runtime provenance. The GitHub Actions evaluation workflow uploads an aggregate JSON report. It does not upload review text.

This is an in-domain benchmark only, not proof of performance on other Persian domains, dialects, or live traffic. Do not advertise performance claims until the report has been inspected and independently reproduced on the intended deployment hardware.

## Latest verified model evaluation

The fixed SnappFood test-split evaluation completed on 2026-11-12 with **93.32% accuracy**, **93.31% balanced accuracy**, and **93.32% macro F1** across 9,033 examples. This is an in-domain baseline, not a general Persian sentiment guarantee. See [MODEL_EVALUATION.md](MODEL_EVALUATION.md) for per-class metrics, confusion matrix, runtime measurements, and the release decision.

The current result supports a private staging deployment or a limited monitored pilot after the operational controls below are configured. It does not approve unrestricted public traffic or external performance/SLA claims.

## Shared local Docker Compose stack

From the repository root, copy `.env.example` to `.env` and set `SENTIMENT_API_KEY` to an independently generated random secret of at least 32 characters before starting FarsiPulse with Compose. Compose sets `SENTIMENT_REQUIRE_API_KEY=true`, so the service refuses to start if the key is missing or too short. Do not commit `.env`. All demo ports bind to loopback only. AtlasRAG now uses PostgreSQL 16 with a GIN-indexed full-text search backend and configured per-tenant API keys; see the production runbook in the repository for deployment details. RelayForge requires separate producer and operator tokens.

## Docker and deployment

```bash
docker build -t farsipulse .
docker run --rm -p 8000:8000 farsipulse
```

The container fetches model weights on first inference. Mount persistent storage at `HF_HOME` for repeat runs. The image runs as a non-root user, uses CPU-only PyTorch, and limits itself to one worker.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Render Blueprint, persistent model cache, API-key setup, and production release checklist. The included [render.yaml](../../render.yaml) is a deployment template; it does not create a live service automatically.

Before public traffic, configure a strong `SENTIMENT_API_KEY` and `SENTIMENT_REQUIRE_API_KEY=true`, HTTPS, edge rate/concurrency limits, monitoring, retention/privacy policies, and an operational rollback process. The Render Blueprint enables fail-closed key enforcement; deployment must supply the secret. API-key validation does not replace rate limiting or abuse controls.

## Model provenance and limitations

- Model: [HooshvareLab/bert-fa-base-uncased-sentiment-snappfood](https://huggingface.co/HooshvareLab/bert-fa-base-uncased-sentiment-snappfood)
- Pinned revision: `8c5d0be5517c4bd5e26f785b1ad60b394a80de07`
- The model is fine-tuned for SnappFood-style review polarity; other domains, dialects, sarcasm, and mixed sentiment may behave differently.
- Binary classification only; no neutral class is implemented.
- CPU inference may be slow; cold-start model loading is slower than subsequent predictions.
- Do not use predictions as the sole basis for consequential decisions about people.

Application code is MIT-licensed. Model weights and datasets remain subject to their upstream terms.
