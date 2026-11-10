from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from .answering import build_grounded_answer
from .chunking import split_text
from .config import get_settings
from .evaluation import evaluate_retrieval
from .retrieval import BM25Retriever
from .schemas import (
    Citation,
    DocumentIn,
    EvaluationRequest,
    EvaluationResponse,
    IngestResponse,
    QueryIn,
    QueryResponse,
)
from .store import SQLiteStore

settings = get_settings()
store = SQLiteStore(settings.database_path)
retriever = BM25Retriever()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Production RAG Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Citation-first document retrieval with deterministic evaluation.",
)


@app.get("/health")
def health():
    return {"status": "ok", "indexed_documents": store.count_documents()}


@app.post("/v1/documents", response_model=IngestResponse, status_code=201)
def ingest_document(payload: DocumentIn, request: Request):
    cfg = request.app.state.settings if hasattr(request.app.state, "settings") else settings
    if len(payload.text) > cfg.max_document_chars:
        raise HTTPException(status_code=413, detail="document exceeds configured character limit")
    chunks = split_text(payload.text, cfg.chunk_size, cfg.chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=422, detail="document contains no indexable text")
    replaced = store.upsert_document(
        payload.document_id, payload.title, payload.source,
        payload.metadata, [chunk.text for chunk in chunks],
    )
    return IngestResponse(
        document_id=payload.document_id,
        chunks_created=len(chunks),
        replaced_existing=replaced,
    )


@app.post("/v1/query", response_model=QueryResponse)
def query_documents(payload: QueryIn, request: Request):
    cfg = request.app.state.settings if hasattr(request.app.state, "settings") else settings
    if len(payload.question) > cfg.max_query_chars:
        raise HTTPException(status_code=413, detail="question exceeds configured character limit")
    top_k = min(payload.top_k or cfg.default_top_k, cfg.max_top_k)
    results = retriever.search(payload.question, store.list_chunks(), top_k)
    results = [item for item in results if item["score"] >= cfg.min_relevance_score]
    citations = [
        Citation(
            chunk_id=item["chunk_id"], document_id=item["document_id"],
            title=item["title"], source=item["source"], text=item["text"],
            score=round(item["score"], 6),
        )
        for item in results
    ]
    return QueryResponse(
        answer=build_grounded_answer(payload.question, results),
        grounded=bool(results),
        citations=citations,
    )


@app.post("/v1/evaluate", response_model=EvaluationResponse)
def evaluate(payload: EvaluationRequest):
    chunks = store.list_chunks()

    def retrieve(question: str, k: int):
        return retriever.search(question, chunks, k)

    metrics = evaluate_retrieval(
        [case.model_dump() for case in payload.cases], retrieve, payload.top_k
    )
    return EvaluationResponse(**metrics)
