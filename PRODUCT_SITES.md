# Product websites

Three independent, responsive product sites are published on Render and linked from their corresponding project READMEs.

| Product | Live website | Project source |
|---|---|---|
| FarsiPulse | https://farsipulse.onrender.com | `projects/persian-sentiment-api/site` |
| AtlasRAG | https://atlasrag-6eab.onrender.com | `projects/production-rag-service/site` |
| RelayForge | https://relayforge-rcpo.onrender.com | `projects/webhook-reliability-platform/site` |

## Design direction

- **FarsiPulse:** bright, Persian-language intelligence brand; mint/forest palette; sentiment snapshot and evaluation section.
- **AtlasRAG:** enterprise knowledge infrastructure; navy/violet palette; evidence cards, tenant isolation and retrieval architecture.
- **RelayForge:** event-delivery engineering; charcoal/lime palette; pipeline visualization, delivery semantics and a local-only outcome explainer.

Each site is a dependency-free static HTML page with responsive layouts, semantic sections, metadata, and accessible interactive states. The previews are illustrative: they do not pretend to call a live model, database, or webhook receiver.

## Publication

All three Render static sites were created in the connected workspace and their initial deployments reported `live` by Render at publication time. The websites are served from the `feat/product-websites-farsipulse-atlasrag-relayforge` branch. Render is configured to deploy subsequent commits on that branch automatically.

## API integration boundary

The API services are separate from these public static sites. No API URL or production credentials are hard-coded into the browser. The websites are currently product/marketing showcases; their interactive examples are local demonstrations, not live inference, retrieval, or webhook delivery. A separate integration pass is required to add authenticated, user-initiated API calls with the right CORS policy and without exposing server-side secrets.
