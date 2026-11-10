from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
ARTIFACT_PATH = ROOT / "artifacts" / "iris_model.joblib"
MODEL_VERSION = "iris-rf-1.0.0"


def main() -> None:
    dataset = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        dataset.data,
        dataset.target,
        test_size=0.2,
        random_state=42,
        stratify=dataset.target,
    )

    model = RandomForestClassifier(
        n_estimators=150,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    artifact = {
        "model": model,
        "model_version": MODEL_VERSION,
        "feature_names": dataset.feature_names,
        "class_names": dataset.target_names.tolist(),
        "test_accuracy": float(accuracy),
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, ARTIFACT_PATH)

    print(f"Saved model: {ARTIFACT_PATH}")
    print(f"Model version: {MODEL_VERSION}")
    print(f"Held-out accuracy: {accuracy:.3f}")


if __name__ == "__main__":
    main()
