# Grounded Document Retrieval API

A small document-search service that retrieves relevant text passages and returns their source metadata. It is designed as the retrieval foundation for a future citation-grounded RAG application.

## Current scope

- Load a small local collection of text documents
- Split documents into paragraph-sized chunks
- Rank chunks with TF-IDF and cosine similarity
- Return source IDs and excerpts with each result
- Expose retrieval through FastAPI

This version does not generate answers with an LLM. It demonstrates and evaluates retrieval separately before a generation layer is introduced.

## Setup

Python 3.11+:

    python -m venv .venv
    python -m pip install -r requirements.txt
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000/docs.

## Try it

    curl -X POST http://127.0.0.1:8000/search -H "Content-Type: application/json" -d '{"query":"How are API requests validated?","top_k":3}'

## Design notes

The index is built from files in data/docs when the application starts. TF-IDF is a lexical baseline: it is lightweight and explainable, but it may miss paraphrases and semantic similarity.

## Roadmap

- [ ] Add a small, versioned retrieval evaluation set
- [ ] Compare TF-IDF with embedding-based retrieval
- [ ] Add document ingestion and metadata validation
- [ ] Add an optional answer-generation layer with citations
- [ ] Add persistence, tests, and Docker support
