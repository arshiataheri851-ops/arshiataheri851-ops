import joblib
from sklearn.tree import DecisionTreeClassifier

from app.model_service import ModelService


def test_prediction_maps_numeric_class_to_human_readable_label(tmp_path):
    model = DecisionTreeClassifier(random_state=42)
    model.fit([[0.0], [0.5], [10.0], [10.5]], [0, 0, 1, 1])

    artifact_path = tmp_path / "model.joblib"
    joblib.dump(
        {
            "model": model,
            "model_version": "test-1",
            "class_names": ["setosa", "versicolor"],
        },
        artifact_path,
    )

    result = ModelService(artifact_path).predict([0.25])

    assert result["label"] == "setosa"
    assert result["model_version"] == "test-1"
    assert 0.0 <= result["confidence"] <= 1.0
