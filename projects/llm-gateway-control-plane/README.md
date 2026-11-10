# LLM Gateway Control Plane

A provider-agnostic API gateway for chat models. It demonstrates model-provider abstraction, priority-aware routing, per-request spend ceilings, bounded retries, and a safe local mock fallback.

## Highlights
- OpenAI-compatible HTTP adapter with API keys read only from environment variables.
- Routing policies for balanced, low-cost, and low-latency requests.
- Estimated-cost budget checks before a provider is called.
- Bounded retries and fallback without exposing provider error payloads.
- Local mock mode that works without credentials and labels simulated output clearly.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set `OPENAI_API_KEY` to enable a remote provider. Optional settings: `OPENAI_BASE_URL` (default `https://api.openai.com/v1`) and `OPENAI_MODEL` (default `gpt-4o-mini`). Without a key, the gateway uses local mock mode.

## API example
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain vector search.","priority":"balanced","max_output_tokens":120,"budget_usd":0.05}'
```

The gateway uses character-count token estimates for preflight budgeting; this is not billing reconciliation. Production deployment should add tenant authentication, distributed rate limiting, durable usage accounting, provider-specific tokenization, and managed secret storage.
