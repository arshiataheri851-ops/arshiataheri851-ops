# Persian Sentiment API

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/persian-sentiment-api.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/persian-sentiment-api.yml)

A production-oriented REST API for Persian (Farsi) sentiment analysis, built with FastAPI and a pretrained Persian BERT model.

**Project status:** first working implementation. This repository includes lazy model loading, Persian text normalization, single and batch inference, health checks, Docker support, automated tests, CI, and an optional evaluation script. No benchmark score is claimed until the evaluation is run and its environment is recorded.

## Architecture at a glance

```text
Client
  |
  v
FastAPI + Pydantic validation
  |
  v
Persian text normalization
  |
  v
Lazy Hugging Face model adapter
  |
  v
Positive / Negative scores
```

## Quick start

Python 3.11+ is supported. For a Windows setup from the **repository root** (without running the PowerShell activation script), follow [the Windows setup guide](../../docs/LOCAL_SETUP_WINDOWS.md).

For any operating system, from this project directory:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API and tests run without downloading model weights. Tests use a fake predictor and do not require the pretrained model.

For real inference, install the optional model dependencies:

```bash
python -m pip install -e ".[inference]"
```

The first real prediction downloads the pinned pretrained model from Hugging Face. The initial download can take time and requires several hundred megabytes of disk space.

Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Health and model-loading state |
| POST | `/v1/sentiment` | Predict one Persian text |
| POST | `/v1/sentiment/batch` | Predict up to 32 texts |

### Single prediction

```bash
curl -X POST http://127.0.0.1:8000/v1/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text":"کیفیت غذا عالی بود و خیلی راضی بودم"}'
```

### Batch prediction

```bash
curl -X POST http://127.0.0.1:8000/v1/sentiment/batch \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"خیلی خوب بود"},{"text":"اصلاً راضی نبودم"}]}'
```

The response contains the normalized text, a binary `positive` / `negative` label, per-class model scores, and the model identifier. The scores are model outputs, not calibrated probabilities or guarantees.

## Model and data provenance

- **Model:** [HooshvareLab/bert-fa-base-uncased-sentiment-snappfood](https://huggingface.co/HooshvareLab/bert-fa-base-uncased-sentiment-snappfood)
- **Pinned model revision:** `8c5d0be5517c4bd5e26f785b1ad60b394a80de07`
- **Model license shown on Hugging Face:** Apache-2.0.
- **Dataset reference:** [ParsiAI/snappfood-sentiment-analysis](https://huggingface.co/datasets/ParsiAI/snappfood-sentiment-analysis)
- **Dataset revision used by evaluation:** `f7127a990026b685fcf3ff2086b74138ec1e9fa6`

The referenced dataset exposes train, validation, and test CSV splits with Persian review text and `HAPPY` / `SAD` labels. Check the dataset publisher's current terms and permissions before using it. The dataset is not copied into this repository.

## Evaluate

Install the optional evaluation dependencies:

```bash
python -m pip install -e ".[inference,evaluation]"
python scripts/evaluate.py
```

The script downloads the pinned test CSV at runtime and prints a classification report and confusion matrix. It does not upload data or publish results. Record the Python version, PyTorch/Transformers versions, hardware, dataset revision, and model revision whenever reporting metrics.

## Tests and quality checks

Tests use a fake predictor, so they do not download model weights:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Docker

```bash
cd projects/persian-sentiment-api
docker build -t persian-sentiment-api .
docker run --rm -p 8000:8000 persian-sentiment-api
```

The model is fetched on the first prediction. For repeat deployments, mount a persistent Hugging Face cache.

## Configuration

Copy `.env.example` to `.env`. The default model ID and immutable revision are documented in `app/config.py`.

## Limitations

- The upstream model was fine-tuned for SnappFood-style review polarity. Performance may differ on other domains, dialects, sarcasm, and mixed-sentiment texts.
- The task is binary; there is no neutral class.
- Model confidence is not a guarantee of correctness or calibration.
- CPU inference may be slower than GPU inference.
- Do not use predictions as the sole basis for consequential decisions about people.

## License

The application code in this folder is MIT-licensed. Model weights and datasets remain subject to their own upstream terms.
