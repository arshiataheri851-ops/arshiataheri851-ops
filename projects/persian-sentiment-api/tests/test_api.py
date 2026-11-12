from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TEST_API_KEY = "test-only-secret-value-at-least-32-chars"


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
    client = make_client(api_key=TEST_API_KEY)
    response = client.post("/v1/sentiment", json={"text": "کیفیت عالی بود"})
    assert response.status_code == 401


def test_valid_api_key_allows_inference() -> None:
    client = make_client(api_key=TEST_API_KEY)
    response = client.post(
        "/v1/sentiment",
        headers={"X-API-Key": TEST_API_KEY},
        json={"text": "کیفیت عالی بود"},
    )
    assert response.status_code == 200


def test_invalid_api_key_is_rejected() -> None:
    client = make_client(api_key=TEST_API_KEY)
    response = client.post(
        "/v1/sentiment",
        headers={"X-API-Key": "wrong-secret"},
        json={"text": "کیفیت عالی بود"},
    )
    assert response.status_code == 401


def test_api_key_must_be_long_enough() -> None:
    try:
        Settings(api_key="too-short")
    except ValueError:
        return
    raise AssertionError("Short API keys must be rejected.")


def test_api_key_is_required_for_batch_prediction():
    client = make_client(api_key=TEST_API_KEY)
    payload = {"items": [{"text": "کیفیت عالی بود"}]}

    missing = client.post("/v1/sentiment/batch", json=payload)
    assert missing.status_code == 401

    invalid = client.post(
        "/v1/sentiment/batch",
        headers={"X-API-Key": "wrong-secret"},
        json=payload,
    )
    assert invalid.status_code == 401

    valid = client.post(
        "/v1/sentiment/batch",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload,
    )
    assert valid.status_code == 200
    assert valid.json()["count"] == 1
    assert valid.json()["predictions"][0]["sentiment"] == "positive"
