from pathlib import Path
from typing import Any

import joblib
import numpy as np


class ModelNotReadyError(RuntimeError):
    """Raised when a trained model artifact is not available."""


class ModelService:
    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path
        self._artifact: dict[str, Any] | None = None

    @property
    def is_ready(self) -> bool:
        return self._artifact is not None or self.artifact_path.is_file()

    def load(self) -> None:
        if not self.artifact_path.is_file():
            raise ModelNotReadyError(
                "Model artifact not found. Run python train.py before starting inference."
            )
        artifact = joblib.load(self.artifact_path)
        if not isinstance(artifact, dict) or "model" not in artifact:
            raise ModelNotReadyError("Model artifact has an unsupported format.")
        self._artifact = artifact

    def predict(self, features: list[float]) -> dict[str, Any]:
        if self._artifact is None:
            self.load()

        assert self._artifact is not None
        model = self._artifact["model"]
        values = np.asarray([features], dtype=float)
        probabilities = model.predict_proba(values)[0]
        class_index = int(np.argmax(probabilities))
        label = str(model.classes_[class_index])
        return {
            "label": label,
            "confidence": float(probabilities[class_index]),
            "model_version": self._artifact["model_version"],
        }
