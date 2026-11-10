# ML Model Serving Platform

A reproducible machine-learning serving example: train a small Iris classifier, save a versioned artifact, and expose predictions through a validated FastAPI service.

## What it demonstrates

- Repeatable training and held-out evaluation
- Model artifact metadata and version information
- Typed inference requests and responses
- Health checks and explicit handling when no artifact exists
- Separation between training and serving code

## Setup

Python 3.11+ is recommended.

    python -m venv .venv
    python -m pip install -r requirements.txt
    python train.py
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000/docs.

## Endpoints

- GET /health — reports whether a trained artifact is available
- POST /predict — predicts an Iris flower class from four numeric features

Example request:

    curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'

## Limitations

This is an educational example using the public Iris dataset. It is not a production deployment. Metrics must be generated locally with the supplied training script. The serialized model artifact is created locally and is not committed.

## Roadmap

- [ ] Add automated tests for model loading and inference
- [ ] Add structured logging and request IDs
- [ ] Add Docker support and CI
- [ ] Add model artifact checksums and compatibility checks
