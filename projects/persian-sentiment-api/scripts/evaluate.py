from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download
from sklearn.metrics import classification_report, confusion_matrix

from app.config import Settings
from app.predictor import HuggingFaceSentimentPredictor

DATASET_REPO = "ParsiAI/snappfood-sentiment-analysis"
DATASET_REVISION = "f7127a990026b685fcf3ff2086b74138ec1e9fa6"
LABEL_MAP = {"HAPPY": "positive", "SAD": "negative"}
BATCH_SIZE = 16


def main() -> None:
    dataset_path = hf_hub_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        filename="test.csv",
        revision=DATASET_REVISION,
    )
    frame = pd.read_csv(Path(dataset_path))
    required_columns = {"comment", "label"}
    if not required_columns.issubset(frame.columns):
        raise ValueError(f"Expected dataset columns: {sorted(required_columns)}")

    texts = frame["comment"].fillna("").astype(str).tolist()
    raw_labels = frame["label"].astype(str).str.upper().tolist()
    unknown_labels = sorted(set(raw_labels) - set(LABEL_MAP))
    if unknown_labels:
        raise ValueError(f"Unexpected dataset labels: {unknown_labels}")

    expected = [LABEL_MAP[label] for label in raw_labels]
    predictor = HuggingFaceSentimentPredictor(Settings())
    predicted: list[str] = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        predictions = predictor.predict_many(batch)
        predicted.extend(item["sentiment"] for item in predictions)

    report = classification_report(
        expected,
        predicted,
        labels=["negative", "positive"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(
        expected,
        predicted,
        labels=["negative", "positive"],
    ).tolist()
    print(
        json.dumps(
            {
                "dataset": DATASET_REPO,
                "dataset_revision": DATASET_REVISION,
                "model": Settings().model_id,
                "model_revision": Settings().model_revision,
                "examples": len(expected),
                "labels": ["negative", "positive"],
                "confusion_matrix": matrix,
                "classification_report": report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
