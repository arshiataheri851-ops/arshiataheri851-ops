# Product websites

Three independent, responsive product sites live alongside their corresponding API projects:

| Product | Site source | Render Static Site service |
|---|---|---|
| FarsiPulse | `projects/persian-sentiment-api/site` | `farsipulse-site` |
| AtlasRAG | `projects/production-rag-service/site` | `atlasrag-site` |
| RelayForge | `projects/webhook-reliability-platform/site` | `relayforge-site` |

## Design direction

- **FarsiPulse:** bright, Persian-language intelligence brand; mint/forest palette; sentiment snapshot and evaluation section.
- **AtlasRAG:** enterprise knowledge infrastructure; navy/violet palette; evidence cards, tenant isolation and retrieval architecture.
- **RelayForge:** event-delivery engineering; charcoal/lime palette; pipeline visualization, delivery semantics and a local-only outcome explainer.

Each site is a dependency-free static HTML page with responsive layouts, semantic sections, metadata, and accessible interactive states. The previews are explicitly labelled illustrative: they do not pretend to call a live model, database, or webhook receiver.

## Render deployment

The root `render.yaml` Blueprint includes one static-site resource per product. Each service publishes its corresponding `site` directory directly; no Node build step or third-party package install is required. Static-site response headers include content-type sniffing protection, a strict referrer policy, and frame protection.

The source is prepared, but the sites are **not yet published**. The Render account previously returned `need_payment_info` while planning the initial Blueprint. Once the account owner completes the required billing setup, re-run the Blueprint plan and review the full resource list before approving any infrastructure changes. Do not assume a live URL exists until Render reports a successful deployment.

## API integration boundary

The API services are separate from these public static sites. No API URL or production credentials are hard-coded into the browser. When the APIs are deployed, a separate integration pass can add authenticated, user-initiated live API calls with the right CORS policy and without exposing server-side secrets.
