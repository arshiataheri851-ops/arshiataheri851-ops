# FarsiPulse production deployment

This guide describes a repeatable Docker deployment. The included `render.yaml`
is a Render Blueprint template; creating a live service still requires access to
the Render account and an explicit deployment by the repository owner.

## Included deployment defaults

- Python 3.11 slim image, non-root `app` user, one Uvicorn worker.
- CPU-only PyTorch; no GPU is assumed.
- PyTorch intra-op threads capped by `SENTIMENT_CPU_THREADS` (default: 2).
- Transformer pipeline batches capped by `SENTIMENT_INFERENCE_BATCH_SIZE` (default: 16).
- Maximum sequence length remains 512 by default; do not reduce it until the
  evaluation report confirms the accuracy/latency trade-off.
- Hugging Face cache is stored at `HF_HOME`; mount persistent storage there
  to avoid downloading the pinned model after every restart.
- API health check: `GET /health`.
- Optional API-key authentication is implemented. The Render Blueprint prompts
  for `SENTIMENT_API_KEY`; set a long random secret before exposing inference.

## Deploy with Render

1. Push this branch and merge the reviewed changes to `main`.
2. In Render, create a Blueprint from the repository and review the proposed
   service before applying it.
3. The blueprint requests a paid Starter web service and a 5 GB persistent
   disk. Confirm the current provider pricing and region availability first.
4. Set `SENTIMENT_API_KEY` in Render to a long random secret. Never commit the
   secret or paste it into source control. Without this setting, inference
   routes remain unauthenticated.
5. Keep the model ID and pinned revision at their defaults unless a new model
   version has been evaluated and intentionally approved.
6. Deploy manually. The blueprint sets `autoDeploy: false` so a code push
   cannot silently trigger a production release.
7. After deployment, check `/health`, then send one controlled Persian test
   request to `POST /v1/sentiment` with the `X-API-Key` header. The first
   inference may take longer while model weights are loaded; later requests
   should reuse the in-process model.

## Required operational controls before public traffic

The service can require an API key on both inference routes and validates text
length (4,000 characters) and batch size (32 items). API-key validation alone
does not provide per-client rate limits, billing, tenant isolation, or abuse
protection. Add those controls at an API gateway or reverse proxy before
accepting public or paid traffic.

For a public endpoint:

- Terminate HTTPS at the hosting provider or a trusted reverse proxy.
- Add request-rate and concurrency limits at the edge; apply stricter limits
  to batch inference.
- Set provider CPU and memory limits and observe peak RSS, cold-start time,
  p50/p95 latency, and throughput before increasing concurrency.
- Keep one worker per container initially. Each worker would load its own model
  copy and multiply memory use.
- Keep the model cache on persistent storage; never bake model weights into
  the image unless image size and release process are intentionally managed.
- Do not log submitted review text. Restrict access to logs and evaluation
  artifacts.
- Define retention, privacy notice, abuse response, monitoring, and rollback
  procedures before accepting real user data.
- Treat model scores as uncalibrated outputs, not guaranteed probabilities.

## Local Docker verification

From the repository root:

```bash
docker build -t farsipulse:local ./projects/persian-sentiment-api
docker run --rm -p 8001:8000 \
  -e SENTIMENT_INFERENCE_BATCH_SIZE=8 \
  -v farsipulse-model-cache:/home/app/.cache/huggingface \
  farsipulse:local
```

Then open `http://127.0.0.1:8001/docs` and check
`http://127.0.0.1:8001/health`. If an API key is configured, include
`X-API-Key` in inference requests.

## Evaluation before release

Install the evaluation extra and run:

```bash
python -m pip install -e ".[inference,evaluation,dev]"
python scripts/evaluate.py --batch-size 8 --output artifacts/report.json
```

The script evaluates the pinned model on the upstream dataset's fixed
`test.csv` split and records accuracy, balanced accuracy, per-class precision,
recall and F1, confusion matrix, throughput, batch latency, and runtime
provenance. The result is an in-domain benchmark only. It is not a substitute
for a separately collected, consented, representative production validation
set. Review the dataset card and its terms before redistributing any dataset
content; the workflow uploads only aggregate metrics, not review text.

A release should not advertise an accuracy or latency number until the
corresponding workflow artifact has been inspected and reproduced on the
intended deployment hardware.
