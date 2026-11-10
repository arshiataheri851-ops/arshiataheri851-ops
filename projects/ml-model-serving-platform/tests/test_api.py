from fastapi.testclient import TestClient

from app.main import create_app


class FakeModelService:
    is_ready = True

    def predict(self, features: list[float]) -> dict[str, str | float]:
        assert len(features) == 4
        return {
            "label": "setosa",
            "confidence": 0.98,
            "model_version": "test-model-1",
        }


def make_client() -> TestClient:
    return TestClient(create_app(model_service=FakeModelService()))


def test_health_reports_model_readiness() -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json()["model_ready"] is True


def test_prediction_returns_model_metadata() -> None:
    response = make_client().post(
        "/predict",
        json={
            "sepal_length": 5.1,
            "sepal_width": 3.5,
            "petal_length": 1.4,
            "petal_width": 0.2,
        },
    )
    assert response.status_code == 200
    assert response.json()["label"] == "setosa"
    assert response.json()["model_version"] == "test-model-1"


def test_invalid_measurement_is_rejected() -> None:
    response = make_client().post(
        "/predict",
        json={
            "sepal_length": -1,
            "sepal_width": 3.5,
            "petal_length": 1.4,
            "petal_width": 0.2,
        },
    )
    assert response.status_code == 422
