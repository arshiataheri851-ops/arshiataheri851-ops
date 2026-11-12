from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakePredictor:
    is_loaded = True

    def predict_many(self, texts: list[str]) -> list[dict[str, object]]:
        results = []
        for text in texts:
            positive = "خوب" in text or "عالی" in text
            results.append(
                {
                    "sentiment": "positive" if positive else "negative",
                    "confidence": 0.91,
                    "scores": {
                        "positive": 0.91 if positive else 0.09,
                        "negative": 0.09 if positive else 0.91,
                    },
                }
            )
        return results


def make_client(api_key: str | None = None) -> TestClient:
    settings = Settings(
        model_id="test-model",
        model_revision="test-revision",
        api_key=api_key,
    )
    return TestClient(create_app(settings=settings, predictor=FakePredictor()))


def test_root_and_health() -> None:
    client = make_client()
    assert client.get("/").status_code == 200
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["model_loaded"] is True
    assert health["model_id"] == "test-model"


def test_single_prediction() -> None:
    response = make_client().post(
        "/v1/sentiment",
        json={"text": "کیفیت غذا عالی بود"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sentiment"] == "positive"
    assert body["language"] == "fa"
    assert body["normalized_text"] == "کیفیت غذا عالی بود"
    assert body["scores"]["positive"] == 0.91


def test_batch_prediction() -> None:
    response = make_client().post(
        "/v1/sentiment/batch",
        json={"items": [{"text": "خیلی خوب بود"}, {"text": "اصلاً راضی نبودم"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["sentiment"] for item in body["predictions"]] == ["positive", "negative"]


def test_blank_text_is_rejected() -> None:
    response = make_client().post("/v1/sentiment", json={"text": "   "})
    assert response.status_code == 422


def test_batch_limit_is_enforced() -> None:
    items = [{"text": "خوب"} for _ in range(33)]
    response = make_client().post("/v1/sentiment/batch", json={"items": items})
    assert response.status_code == 422


def test_api_key_is_required_when_configured() -> None:
    client = make_client(api_key="test-secret")
    response = client.post("/v1/sentiment", json={"text": "کیفیت عالی بود"})
    assert response.status_code == 401


def test_valid_api_key_allows_inference() -> None:
    client = make_client(api_key="test-secret")
    response = client.post(
        "/v1/sentiment",
        headers={"X-API-Key": "test-secret"},
        json={"text": "کیفیت عالی بود"},
    )
    assert response.status_code == 200


def test_invalid_api_key_is_rejected() -> None:
    client = make_client(api_key="test-secret")
    response = client.post(
        "/v1/sentiment",
        headers={"X-API-Key": "wrong-secret"},
        json={"text": "کیفیت عالی بود"},
    )
    assert response.status_code == 401
