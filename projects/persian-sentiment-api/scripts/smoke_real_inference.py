"""Run end-to-end API inference against the pinned, real Hugging Face model.

This is intentionally separate from the fast unit tests, which use a fake predictor.
"""
from __future__ import annotations

import json
import math

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.predictor import HuggingFaceSentimentPredictor


def validate_prediction(payload: dict[str, object]) -> None:
    assert payload["sentiment"] in {"positive", "negative"}
    confidence = float(payload["confidence"])
    assert math.isfinite(confidence) and 0.0 <= confidence <= 1.0

    scores = payload["scores"]
    assert isinstance(scores, dict)
    assert set(scores) == {"positive", "negative"}
    values = [float(scores["positive"]), float(scores["negative"])]
    assert all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in values)
    assert math.isclose(sum(values), 1.0, rel_tol=0.02, abs_tol=0.02)


def main() -> None:
    settings = Settings()
    predictor = HuggingFaceSentimentPredictor(settings)
    client = TestClient(create_app(settings=settings, predictor=predictor))

    single_response = client.post(
        "/v1/sentiment",
        json={"text": "کیفیت غذا عالی بود و از خریدم خیلی راضی هستم"},
    )
    single_response.raise_for_status()
    single = single_response.json()
    validate_prediction(single)

    batch_response = client.post(
        "/v1/sentiment/batch",
        json={
            "items": [
                {"text": "محصول بسیار باکیفیت و کاربردی بود"},
                {"text": "کیفیت بسیار بد بود و اصلاً راضی نبودم"},
            ]
        },
    )
    batch_response.raise_for_status()
    batch = batch_response.json()
    assert batch["count"] == 2
    assert len(batch["predictions"]) == 2
    for prediction in batch["predictions"]:
        validate_prediction(prediction)

    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["model_loaded"] is True

    print(
        json.dumps(
            {
                "status": "real_model_inference_passed",
                "model_id": settings.model_id,
                "model_revision": settings.model_revision,
                "single_prediction": single,
                "batch_predictions": batch["predictions"],
                "health": health,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
