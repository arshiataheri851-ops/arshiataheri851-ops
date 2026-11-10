![Arshia Taheri — AI Engineering Portfolio](assets/profile-banner.svg)

<h1 align="center">Arshia Taheri</h1>
<h3 align="center">AI / ML Engineering · LLM Applications · Backend Systems</h3>

<p align="center">
  <a href="https://github.com/arshiataheri851-ops">GitHub</a> ·
  <a href="https://github.com/arshiataheri851-ops/arshia-taheri851">Portfolio</a> ·
  <a href="https://www.linkedin.com/in/arshia-taheri-5b85b33b2/">LinkedIn</a>
</p>

---

## Profile

I work across **applied machine learning, generative AI, backend engineering, and data systems**. My focus is on building useful, maintainable software around models: from data preparation and evaluation to API integration, deployment, and monitoring.

I am especially interested in production-oriented AI systems, Persian-language NLP, retrieval-based applications, and reliable model-serving infrastructure.

## Engineering focus

| Area | Focus |
|---|---|
| **Applied ML** | Predictive modeling, classification, model evaluation, feature engineering |
| **Generative AI** | LLM applications, RAG pipelines, embeddings, agent workflows |
| **NLP & Speech** | Text classification, sentiment analysis, Persian-language use cases, ASR evaluation |
| **Backend** | Python services, REST APIs, FastAPI, Django, integrations |
| **Data engineering** | SQL, PostgreSQL, ETL workflows, data processing |
| **MLOps & delivery** | Model serving, Docker, Kubernetes, experiment tracking, monitoring |

## Technology

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white"/>
  <img alt="TensorFlow" src="https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white"/>
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white"/>
  <img alt="Hugging Face" src="https://img.shields.io/badge/Hugging_Face-FFD21E?style=flat-square&logo=huggingface&logoColor=black"/>
  <img alt="Pandas" src="https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white"/>
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white"/>
</p>
<p>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img alt="Django" src="https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white"/>
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white"/>
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white"/>
  <img alt="Kubernetes" src="https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white"/>
  <img alt="MLflow" src="https://img.shields.io/badge/MLflow-0194E2?style=flat-square&logo=mlflow&logoColor=white"/>
  <img alt="Redis" src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white"/>
  <img alt="Apache Kafka" src="https://img.shields.io/badge/Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white"/>
</p>

## Featured projects

[![Advanced engineering project checks](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/advanced-engineering-projects.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/advanced-engineering-projects.yml)

### 1. [Persian Sentiment API](projects/persian-sentiment-api/README.md)
[![Persian Sentiment API CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/persian-sentiment-api.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/persian-sentiment-api.yml)

FastAPI inference service for Persian review sentiment using a pinned pretrained model. Includes conservative normalization, single and batch inference, health checks, Docker support, automated tests, CI, and an optional reproducible evaluation script. Benchmark scores are intentionally not claimed until measured.

### 2. [ML Model Serving Platform](projects/ml-model-serving-platform/README.md)
A learning implementation of a versioned scikit-learn model artifact, reproducible training script, held-out evaluation, and validated FastAPI inference endpoint. Uses the public Iris dataset.

### 3. [Grounded Document Retrieval API](projects/grounded-document-retrieval/README.md)
A source-aware document retrieval baseline using TF-IDF, cosine similarity, local text documents, and FastAPI. This is the retrieval layer for a future RAG system; it does not claim LLM-generated answers.

### 4. [Market Intelligence & Risk Analytics](projects/market-intelligence-risk-engine/README.md)
An educational OHLCV processing pipeline with input validation, moving averages, daily-change monitoring, and CSV reporting. Includes synthetic sample data and does not provide trading recommendations.

### 5. [Production RAG Service](projects/production-rag-service/README.md)
A citation-first retrieval service using SQLite, BM25 ranking, extractive evidence selection, and retrieval evaluation. It explicitly does not claim LLM-generated answers.

### 6. [Workflow Orchestration Engine](projects/workflow-orchestration-engine/README.md)
A dependency-aware DAG runner with cycle detection, topological execution, retries, per-step outcomes, and a FastAPI interface. It is a synchronous reference implementation with explicitly documented durability limits.

### 7. [Webhook Reliability Platform](projects/webhook-reliability-platform/README.md)
A transport-agnostic event delivery core with idempotent ingestion, HMAC-SHA256 signatures, bounded retries, and dead-letter handling. The sender is injected so automated tests do not make real network calls.

### 8. [ML Feature Store](projects/ml-feature-store/README.md)
A SQLite-backed feature store with typed feature schemas, versioned entity values, batch lookup, and TTL-based freshness metadata.

### 9. [Intelligent Recommendation Platform](projects/intelligent-recommendation-platform/README.md)
A FastAPI recommendation service with SQLite interaction history, weighted view/click/purchase feedback, cold-start popularity fallback, seen-item suppression, and human-readable ranking explanations. The ranker is a transparent baseline, not a trained model.

## Profile branding

- [Profile avatar artwork (SVG)](assets/profile-avatar.svg)
- [Social preview artwork (SVG)](assets/social-preview.svg)
- [Profile finishing steps](docs/PROFILE_FINISHING_STEPS.md)

## Local development

- [Windows setup guide for running Persian Sentiment API](docs/LOCAL_SETUP_WINDOWS.md)

## Project roadmap

- [Portfolio project roadmap](docs/PROJECT_ROADMAP.md)
- [Reusable project showcase template](docs/PROJECT_SHOWCASE_TEMPLATE.md)

## How I approach engineering

- **Evidence over claims:** document measurable results and evaluation methodology.
- **Reliable delivery:** use clear interfaces, tests, version control, and reproducible setup steps.
- **Operational thinking:** consider latency, observability, security, and maintainability.
- **Clear communication:** document assumptions, decisions, limitations, and handover details.

## Contact

- GitHub: [@arshiataheri851-ops](https://github.com/arshiataheri851-ops)
- LinkedIn: [Arshia Taher](https://www.linkedin.com/in/arshia-taher-5b85b33b2/)

---

<p align="center"><sub>Building practical AI systems with strong software engineering foundations.</sub></p>
