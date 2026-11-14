# FarsiPulse model evaluation

**Decision:** suitable for a controlled staging deployment and a limited, monitored pilot; not yet approved for unrestricted public or high-impact use.

## Reproducible run

- Workflow: [FarsiPulse Model Evaluation](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43306583185)
- Evaluated: 2026-11-12
- Model: `HooshvareLab/bert-fa-base-uncased-sentiment-snappfood`
- Model revision: `8c5d0be5517c4bd5e26f785b1ad60b394a80de07`
- Dataset: `ParsiAI/snappfood-sentiment-analysis`, fixed upstream `test.csv`
- Dataset revision: `f7127a990026b685fcf3ff2086b74138ec1e9fa6`
- Usable examples: 9,033 (4,547 negative; 4,486 positive); no rows excluded
- Runtime: Python 3.11.18, PyTorch 2.15.0+cpu, CPU-only GitHub-hosted runner
- Inference configuration: max sequence length 512, batch size 16, 2 CPU threads

## Quality metrics

| Metric | Result |
|---|---:|
| Accuracy | 93.32% |
| Balanced accuracy | 93.31% |
| Macro precision | 93.39% |
| Macro recall | 93.31% |
| Macro F1 | 93.32% |
| Weighted F1 | 93.32% |

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Negative | 91.85% | 95.18% | 93.49% | 4,547 |
| Positive | 94.93% | 91.44% | 93.15% | 4,486 |

Confusion matrix (rows = actual, columns = predicted; order: negative, positive):

|  | Predicted negative | Predicted positive |
|---|---:|---:|
| Actual negative | 4,328 | 219 |
| Actual positive | 384 | 4,102 |

The model misses more positive examples as negative (384) than negative examples as positive (219) on this split. Whether that trade-off is acceptable depends on the product use case and should be reviewed with representative users.

## Runtime measurements

| Measurement | Result |
|---|---:|
| Total evaluation time | 620.11 s |
| Throughput | 14.57 examples/s |
| Mean batch latency | 1.10 s |
| p50 batch latency | 0.99 s |
| p95 batch latency | 1.94 s |
| Batch count | 565 |

These are measurements from the GitHub-hosted CPU runner, not a production capacity promise. Batch latency is not single-request API latency. Repeat the measurement on the actual target instance before setting throughput or latency commitments.

## Release assessment

The measured quality is a credible initial baseline for SnappFood-style binary review sentiment. It is not evidence of general Persian sentiment performance across other domains, dialects, sarcasm, mixed sentiment, or live traffic. The model has no neutral class and its scores are not calibrated probabilities.

**Allowed next step:** deploy privately to a staging environment or a limited opt-in pilot after configuring a strong `SENTIMENT_API_KEY`, HTTPS, edge rate/concurrency limits, log redaction, monitoring, and rollback. Use synthetic or consented test data first.

**Not approved yet:** unrestricted public traffic, paid SLA/accuracy claims, or consequential decisions based solely on predictions. Before those, evaluate a separately collected, consented, representative, held-out dataset and repeat performance/memory tests on the intended deployment hardware.

The CI artifact contains aggregate metrics only; review text is not included.
