# Portfolio Project Roadmap

This roadmap tracks the portfolio projects and distinguishes working prototypes from projects that have completed local verification.

## Published projects

| Project | Current status | Next verification step |
|---|---|---|
| Persian Sentiment API | First working implementation with API, model adapter, tests, Docker, CI, and evaluation script | Run CI and record actual evaluation metrics |
| ML Model Serving Platform | Training and inference prototype using the Iris dataset | Add and run API/model tests; verify artifact loading |
| Grounded Document Retrieval API | TF-IDF retrieval prototype with source metadata and FastAPI | Add retrieval tests and a small relevance evaluation set |
| Market Intelligence & Risk Analytics | CSV-based OHLCV analytics prototype using synthetic sample data | Add validation tests and run the sample pipeline |

## Next project milestones

### 1. Strengthen model serving

- Add tests for valid and invalid inference requests.
- Record the training environment and measured held-out metrics.
- Add Docker support and CI after local verification.
- Add artifact integrity and compatibility checks.

### 2. Evolve document retrieval into RAG

- Create a small, versioned question-to-source evaluation set.
- Compare lexical retrieval with embedding-based retrieval.
- Add document ingestion and metadata validation.
- Add an optional generation layer that cites retrieved source passages.
- Evaluate retrieval quality separately from answer quality.

### 3. Improve market data analytics

- Add tests for malformed, missing, and inconsistent OHLCV rows.
- Make rolling-window and alert thresholds configurable.
- Add a read-only API and dashboard only after the data pipeline is verified.
- Keep all examples synthetic or clearly attributed to their source.

## Repository quality checklist

Before marking a project ready for public showcase:

- [ ] Clear problem statement and intended users.
- [ ] Architecture diagram and data-flow explanation.
- [ ] Reproducible setup instructions.
- [ ] Dependency and environment configuration.
- [ ] Tests that have actually been run.
- [ ] Evaluation methodology and measured results.
- [ ] Screenshots or a short demo where relevant.
- [ ] Limitations, security notes, and license.
- [ ] No credentials, private datasets, or confidential employer code.

A project marked prototype is useful portfolio work, but it must not be described as production-ready until the relevant checks have been completed.
