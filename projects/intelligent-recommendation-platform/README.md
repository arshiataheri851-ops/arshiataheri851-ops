# Intelligent Recommendation Platform

A production-minded recommendation API with event-driven user profiles, cold-start handling, explainable ranking, and persistent interaction history.

## What it demonstrates
- A recommendation pipeline that separates catalog data, event storage, ranking, and HTTP delivery.
- Weighted implicit feedback: views, clicks, and purchases contribute different strengths.
- Cold-start recommendations based on item popularity.
- Seen-item suppression and human-readable recommendation explanations.
- SQLite persistence with parameterized SQL and automated API/core tests.

## Architecture
```text
Client -> FastAPI -> RecommendationService -> EventStore (SQLite)
                                  |
                                  +-> Candidate scoring -> Explanation
```

## Run locally
```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Example
```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-42","item_id":"course-python","event_type":"purchase"}'

curl "http://127.0.0.1:8000/recommendations/user-42?limit=3"
```

## API
- `GET /health`
- `POST /events` — record a view, click, or purchase.
- `GET /recommendations/{user_id}?limit=5` — ranked items with explanations.

## Configuration
Set `RECOMMENDER_DB_PATH` to choose the SQLite database location. The default is `recommendations.db` in the working directory.

## Scope and limitations
The included catalog is intentionally small and illustrative. The ranking algorithm is a transparent baseline, not a claim of production-scale personalization. Offline ranking metrics, A/B testing, distributed event ingestion, and a learned ranker are natural next steps.
