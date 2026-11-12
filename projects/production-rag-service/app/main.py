"""AtlasRAG: citation-first retrieval API with indexed storage."""

from fastapi import FastAPI, HTTPException, Query, Request, status

from .answering import build_grounded_answer
from .chunking import split_text
from .config import Settings, get_settings
from .evaluation import evaluate_retrieval
from .retrieval import BM25Retriever
from .schemas import (
    BatchIngestResponse,
    Citation,
    DocumentBatchIn,
    DocumentIn,
    EvaluationRequest,
    EvaluationResponse,
    IngestResponse,
    QueryIn,
    QueryResponse,
)
from .store import SQLiteStore


def create_app(
    settings: Settings | None = None,
    store: SQLiteStore | None = None,
    retriever: BM25Retriever | None = None,
) -> FastAPI:
    cfg = settings or get_settings()
    database = store or SQLiteStore(cfg.database_path)
    ranker = retriever or BM25Retriever()

    api = FastAPI(
        title="AtlasRAG — Evidence Retrieval API",
        version="1.2.0",
        description=(
            "A citation-first retrieval service with persistent full-text indexing. "
            "It returns extractive evidence and abstains when evidence is missing."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )
    api.state.settings = cfg
    api.state.store = database
    api.state.retriever = ranker

    def ingest_one(payload: DocumentIn, request: Request) -> IngestResponse:
        current_settings = request.app.state.settings
        if len(payload.text) > current_settings.max_document_chars:
            raise HTTPException(
                status_code=413,
                detail=f"Document '{payload.document_id}' exceeds the configured size limit.",
            )
        chunks = split_text(
            payload.text, current_settings.chunk_size, current_settings.chunk_overlap
        )
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail=f"Document '{payload.document_id}' contains no indexable text.",
            )
        replaced = request.app.state.store.upsert_document(
            payload.document_id, payload.title, payload.source, payload.metadata,
            [chunk.text for chunk in chunks],
        )
        return IngestResponse(
            document_id=payload.document_id,
            chunks_created=len(chunks),
            replaced_existing=replaced,
        )

    def retrieve(question: str, top_k: int, request: Request) -> list[dict]:
        storage = request.app.state.store
        if hasattr(storage, "search_chunks"):
            return storage.search_chunks(question, top_k)
        return request.app.state.retriever.search(question, storage.list_chunks(), top_k)

    @api.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {
            "service": "atlasrag",
            "version": api.version,
            "docs": "/docs",
            "health": "/health",
        }

    @api.get("/health", tags=["service"])
    def health(request: Request) -> dict[str, int | str]:
        storage = request.app.state.store
        return {
            "status": "ok",
            "indexed_documents": storage.count_documents(),
            "indexed_chunks": storage.count_chunks() if hasattr(storage, "count_chunks")
            else len(storage.list_chunks()),
        }

    @api.post(
        "/v1/documents",
        response_model=IngestResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    def ingest_document(payload: DocumentIn, request: Request) -> IngestResponse:
        return ingest_one(payload, request)

    @api.post(
        "/v1/documents/batch",
        response_model=BatchIngestResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    def ingest_documents_batch(
        payload: DocumentBatchIn, request: Request
    ) -> BatchIngestResponse:
        results = [ingest_one(document, request) for document in payload.documents]
        return BatchIngestResponse(accepted=len(results), results=results)

    @api.get("/v1/documents", tags=["documents"])
    def list_documents(
        request: Request,
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, str | int | None]]:
        return request.app.state.store.list_documents(limit=limit, offset=offset)

    @api.delete("/v1/documents/{document_id}", tags=["documents"])
    def delete_document(document_id: str, request: Request) -> dict[str, bool | str]:
        deleted = request.app.state.store.delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"document_id": document_id, "deleted": True}

    @api.post("/v1/query", response_model=QueryResponse, tags=["retrieval"])
    def query_documents(payload: QueryIn, request: Request) -> QueryResponse:
        current_settings = request.app.state.settings
        if len(payload.question) > current_settings.max_query_chars:
            raise HTTPException(status_code=413, detail="Question exceeds the configured size limit.")
        top_k = min(payload.top_k or current_settings.default_top_k, current_settings.max_top_k)
        results = retrieve(payload.question, top_k, request)
        results = [
            item for item in results
            if item["score"] >= current_settings.min_relevance_score
        ]
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
            retrieval_method="sqlite_fts5",
        )

    @api.post("/v1/evaluate", response_model=EvaluationResponse, tags=["evaluation"])
    def evaluate(payload: EvaluationRequest, request: Request) -> EvaluationResponse:
        metrics = evaluate_retrieval(
            [case.model_dump() for case in payload.cases],
            lambda question, k: retrieve(question, k, request),
            payload.top_k,
        )
        return EvaluationResponse(**metrics)

    return api


app = create_app()
