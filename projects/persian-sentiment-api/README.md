# FarsiPulse — Persian Sentiment Intelligence API

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

FarsiPulse is a typed REST service for binary Persian review sentiment inference. It combines conservative Persian normalization, FastAPI request validation, lazy Hugging Face model loading, batch inference, and reproducible evaluation hooks.

## What is implemented

- Single-text and batch prediction endpoints (batch capped at 32 items).
- Pydantic request/response contracts and blank-input rejection.
- Persian Arabic-letter normalization without stripping meaningful ZWNJ characters.
- Lazy model initialization with thread-safe first load.
- Pinned Hugging Face model revision; no model download is needed to run the API tests.
- Docker image, health endpoint, evaluation script, and CI-ready tests.

## Architecture

```text
HTTP Client
    |
    v
FastAPI Router + Pydantic Contracts
    |
    v
Persian Text Normalizer
    |
    v
Thread-safe Hugging Face Adapter (lazy load)
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

## Tests and lint

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Tests use a deterministic fake predictor and do not download model weights.

## Evaluation

```bash
python -m pip install -e ".[inference,evaluation]"
python scripts/evaluate.py
```

The evaluation script uses pinned upstream model/data revisions and reports metrics locally. Do not publish performance claims without recording the exact model and dataset revisions, runtime versions, hardware, and test split.

## Docker

```bash
docker build -t farsipulse .
docker run --rm -p 8000:8000 farsipulse
```

The container fetches model weights on first inference. Mount a persistent Hugging Face cache for repeat runs.

## Model provenance and limitations

- Model: [HooshvareLab/bert-fa-base-uncased-sentiment-snappfood](https://huggingface.co/HooshvareLab/bert-fa-base-uncased-sentiment-snappfood)
- Pinned revision: `8c5d0be5517c4bd5e26f785b1ad60b394a80de07`
- The model is fine-tuned for SnappFood-style review polarity; other domains, dialects, sarcasm, and mixed sentiment may behave differently.
- Binary classification only; no neutral class is implemented.
- CPU inference may be slow.
- Do not use predictions as the sole basis for consequential decisions about people.

Application code is MIT-licensed. Model weights and datasets remain subject to their upstream terms.
