"""Evaluate the pinned model on the upstream dataset's fixed test split.

The report records provenance and runtime measurements. It does not claim that
this domain-specific benchmark represents all Persian-language use cases.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from huggingface_hub import hf_hub_download
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
)

from app.config import Settings
from app.normalization import normalize_persian_text
from app.predictor import HuggingFaceSentimentPredictor

DATASET_REPO = "ParsiAI/snappfood-sentiment-analysis"
DATASET_REVISION = "f7127a990026b685fcf3ff2086b74138ec1e9fa6"
LABEL_MAP = {"HAPPY": "positive", "SAD": "negative"}


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=None, choices=range(1, 33))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    base_settings = Settings()
    settings = Settings(
        inference_batch_size=args.batch_size or base_settings.inference_batch_size
    )
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

    raw_texts = frame["comment"].fillna("").astype(str).tolist()
    raw_labels = frame["label"].fillna("").astype(str).str.upper().tolist()
    unknown_labels = sorted(set(raw_labels) - set(LABEL_MAP) - {""})
    if unknown_labels:
        raise ValueError(f"Unexpected dataset labels: {unknown_labels}")

    examples = [
        (normalize_persian_text(text), LABEL_MAP[label])
        for text, label in zip(raw_texts, raw_labels, strict=True)
        if text.strip() and label in LABEL_MAP
    ]
    if not examples:
        raise ValueError("The pinned test split contains no usable labelled examples.")

    texts = [item[0] for item in examples]
    expected = [item[1] for item in examples]
    predictor = HuggingFaceSentimentPredictor(settings)
    predicted: list[str] = []
    batch_durations: list[float] = []
    started = time.perf_counter()

    for offset in range(0, len(texts), settings.inference_batch_size):
        batch = texts[offset : offset + settings.inference_batch_size]
        batch_started = time.perf_counter()
        predictions = predictor.predict_many(batch)
        batch_durations.append(time.perf_counter() - batch_started)
        predicted.extend(item["sentiment"] for item in predictions)

    elapsed = time.perf_counter() - started
    report: dict[str, Any] = {
        "status": "completed",
        "model": {
            "id": settings.model_id,
            "revision": settings.model_revision,
            "max_sequence_length": settings.max_sequence_length,
            "inference_batch_size": settings.inference_batch_size,
            "cpu_threads": settings.cpu_threads,
        },
        "dataset": {
            "repo": DATASET_REPO,
            "revision": DATASET_REVISION,
            "file": "test.csv",
            "usable_examples": len(expected),
            "excluded_rows": len(frame) - len(expected),
            "labels": ["negative", "positive"],
            "split_policy": "upstream fixed test split; no local random resplit",
        },
        "metrics": {
            "accuracy": accuracy_score(expected, predicted),
            "balanced_accuracy": balanced_accuracy_score(expected, predicted),
            "classification_report": classification_report(
                expected,
                predicted,
                labels=["negative", "positive"],
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(
                expected,
                predicted,
                labels=["negative", "positive"],
            ).tolist(),
        },
        "performance": {
            "elapsed_seconds": elapsed,
            "examples_per_second": len(expected) / elapsed if elapsed else None,
            "batch_latency_seconds_mean": statistics.mean(batch_durations),
            "batch_latency_seconds_p50": percentile(batch_durations, 0.50),
            "batch_latency_seconds_p95": percentile(batch_durations, 0.95),
            "batch_count": len(batch_durations),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
        },
        "interpretation": (
            "This is an in-domain benchmark on the upstream fixed test split. "
            "It is not evidence of performance on other domains, dialects, or live traffic."
        ),
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
