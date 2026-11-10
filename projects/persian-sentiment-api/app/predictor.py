from collections.abc import Sequence
from typing import Any

from app.config import Settings

_LABEL_MAP = {
    "happy": "positive",
    "positive": "positive",
    "pos": "positive",
    "sad": "negative",
    "negative": "negative",
    "neg": "negative",
}


class HuggingFaceSentimentPredictor:
    """Lazy CPU-first adapter around a Hugging Face text-classification pipeline."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pipeline: Any | None = None

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def _load_pipeline(self) -> Any:
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    'Model dependencies are missing. Install with: pip install -e ".[inference]"'
                ) from exc

            self._pipeline = pipeline(
                task="text-classification",
                model=self.settings.model_id,
                tokenizer=self.settings.model_id,
                revision=self.settings.model_revision,
                device=-1,
            )
        return self._pipeline

    @staticmethod
    def _canonical_label(raw_label: str) -> str:
        label = _LABEL_MAP.get(raw_label.strip().lower())
        if label is None:
            raise RuntimeError(f"Unexpected model label: {raw_label!r}")
        return label

    def predict_many(self, texts: Sequence[str]) -> list[dict[str, Any]]:
        if not texts:
            return []

        classifier = self._load_pipeline()
        raw_outputs = classifier(
            list(texts),
            top_k=None,
            truncation=True,
            max_length=self.settings.max_sequence_length,
        )

        # Transformers returns a list of label dictionaries for each input text.
        if len(texts) == 1 and raw_outputs and isinstance(raw_outputs[0], dict):
            raw_outputs = [raw_outputs]

        if len(raw_outputs) != len(texts):
            raise RuntimeError("The model returned an unexpected number of predictions.")

        predictions: list[dict[str, Any]] = []
        for output in raw_outputs:
            scores: dict[str, float] = {}
            for item in output:
                canonical = self._canonical_label(str(item["label"]))
                scores[canonical] = float(item["score"])

            if set(scores) != {"positive", "negative"}:
                raise RuntimeError("The model did not return both expected sentiment labels.")

            sentiment = max(scores, key=scores.get)
            predictions.append(
                {
                    "sentiment": sentiment,
                    "confidence": scores[sentiment],
                    "scores": scores,
                }
            )
        return predictions
