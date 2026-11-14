"""AtlasRAG: tenant-isolated, citation-first retrieval API."""

import hashlib
import hmac

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import Response

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
from .observability import audit_event, instrument_api, metrics_response
from .postgres_store import PostgresStore
from .store import SQLiteStore, TenantDocumentConflict


def resolve_tenant(
    request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> str:
    """Authenticate a tenant using a high-entropy API key; fail closed by default."""
    settings = request.app.state.settings
    if not settings.auth_required:
        return "local"
    if not x_api_key or not 32 <= len(x_api_key) <= 256 or not x_api_key.isascii():
        raise HTTPException(status_code=401, detail="A valid X-API-Key header is required.")
    supplied_digest = hashlib.sha256(x_api_key.encode("ascii")).digest()
    matched_tenant = None
    for tenant_id, expected_key in settings.tenant_api_keys.items():
        expected_digest = hashlib.sha256(expected_key.encode("ascii")).digest()
        if hmac.compare_digest(supplied_digest, expected_digest):
            matched_tenant = tenant_id
    if matched_tenant is None:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return matched_tenant


def create_app(
    settings: Settings | None = None,
    store: SQLiteStore | PostgresStore | None = None,
    retriever: BM25Retriever | None = None,
) -> FastAPI:
    cfg = settings or get_settings()
    database = store or (
        PostgresStore(cfg.database_url) if cfg.database_url else SQLiteStore(cfg.database_path)
    )
    ranker = retriever or BM25Retriever()

    api = FastAPI(
        title="AtlasRAG — Tenant-isolated Evidence Retrieval API",
        version="2.0.0",
        description=(
            "Authenticated multi-tenant retrieval. Every document operation is scoped "
            "to the tenant identified by its API key."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )
    api.state.settings = cfg
    api.state.store = database
    api.state.retriever = ranker
    instrument_api(api)

    def ingest_one(payload: DocumentIn, request: Request, tenant_id: str) -> IngestResponse:
        current_settings = request.app.state.settings
        if len(payload.text) > current_settings.max_document_chars:
            raise HTTPException(status_code=413, detail="Document exceeds the configured size limit.")
        chunks = split_text(payload.text, current_settings.chunk_size, current_settings.chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=422, detail="Document contains no indexable text.")
        try:
            replaced = request.app.state.store.upsert_document(
                payload.document_id, payload.title, payload.source, payload.metadata,
                [chunk.text for chunk in chunks], tenant_id=tenant_id,
            )
        except TenantDocumentConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        audit_event(
            "document.upsert", tenant_id, document_id=payload.document_id,
            outcome="replaced" if replaced else "created",
        )
        return IngestResponse(
            document_id=payload.document_id, chunks_created=len(chunks),
            replaced_existing=replaced,
        )

    def retrieve(question: str, top_k: int, request: Request, tenant_id: str) -> list[dict]:
        storage = request.app.state.store
        if hasattr(storage, "search_chunks"):
            results = storage.search_chunks(question, top_k, tenant_id=tenant_id)
        else:
            results = request.app.state.retriever.search(
                question, storage.list_chunks(tenant_id=tenant_id), top_k
            )
        threshold = request.app.state.settings.min_relevance_score
        return [item for item in results if item["score"] >= threshold]

    @api.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {"service": "atlasrag", "version": api.version, "docs": "/docs", "health": "/health"}

    @api.get("/health", tags=["service"])
    def health(request: Request) -> dict[str, str]:
        # Verify the backing database is reachable without exposing tenant data.
        try:
            healthy = request.app.state.store.health_check()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
        if not healthy:
            raise HTTPException(status_code=503, detail="Database is unavailable.")
        return {"status": "ok", "service": "atlasrag"}

    @api.post(
        "/v1/documents", response_model=IngestResponse,
        status_code=status.HTTP_201_CREATED, tags=["documents"],
    )
    def ingest_document(
        payload: DocumentIn, request: Request, tenant_id: str = Depends(resolve_tenant)
    ) -> IngestResponse:
        return ingest_one(payload, request, tenant_id)

    @api.post(
        "/v1/documents/batch", response_model=BatchIngestResponse,
        status_code=status.HTTP_201_CREATED, tags=["documents"],
    )
    def ingest_documents_batch(
        payload: DocumentBatchIn, request: Request,
        tenant_id: str = Depends(resolve_tenant),
    ) -> BatchIngestResponse:
        current_settings = request.app.state.settings
        prepared = []
        for document in payload.documents:
            if len(document.text) > current_settings.max_document_chars:
                raise HTTPException(status_code=413, detail="A document exceeds the configured size limit.")
            chunks = split_text(document.text, current_settings.chunk_size, current_settings.chunk_overlap)
            if not chunks:
                raise HTTPException(status_code=422, detail="A document contains no indexable text.")
            prepared.append({
                "document_id": document.document_id, "title": document.title,
                "source": document.source, "metadata": document.metadata,
                "chunks": [chunk.text for chunk in chunks],
            })
        try:
            replaced = request.app.state.store.upsert_documents_batch(prepared, tenant_id=tenant_id)
        except TenantDocumentConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        results = [
            IngestResponse(
                document_id=document.document_id, chunks_created=len(item["chunks"]),
                replaced_existing=was_replaced,
            )
            for document, item, was_replaced in zip(payload.documents, prepared, replaced, strict=True)
        ]
        audit_event("document.batch_upsert", tenant_id, item_count=len(results))
        return BatchIngestResponse(accepted=len(results), results=results)

    @api.get("/v1/documents", tags=["documents"])
    def list_documents(
        request: Request, limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        tenant_id: str = Depends(resolve_tenant),
    ) -> list[dict]:
        documents = request.app.state.store.list_documents(
            limit=limit, offset=offset, tenant_id=tenant_id
        )
        audit_event("document.list", tenant_id, item_count=len(documents))
        return documents

    @api.delete("/v1/documents/{document_id}", tags=["documents"])
    def delete_document(
        document_id: str, request: Request, tenant_id: str = Depends(resolve_tenant)
    ) -> dict[str, bool | str]:
        deleted = request.app.state.store.delete_document(document_id, tenant_id=tenant_id)
        if not deleted:
            # Same response for missing and foreign-owned IDs prevents enumeration.
            raise HTTPException(status_code=404, detail="Document not found.")
        audit_event("document.delete", tenant_id, document_id=document_id)
        return {"document_id": document_id, "deleted": True}

    @api.post("/v1/query", response_model=QueryResponse, tags=["retrieval"])
    def query_documents(
        payload: QueryIn, request: Request, tenant_id: str = Depends(resolve_tenant)
    ) -> QueryResponse:
        current_settings = request.app.state.settings
        if len(payload.question) > current_settings.max_query_chars:
            raise HTTPException(status_code=413, detail="Question exceeds the configured size limit.")
        top_k = min(payload.top_k or current_settings.default_top_k, current_settings.max_top_k)
        results = retrieve(payload.question, top_k, request, tenant_id)
        citations = [
            Citation(
                chunk_id=item["chunk_id"], document_id=item["document_id"],
                title=item["title"], source=item["source"], text=item["text"],
                score=round(item["score"], 6),
            ) for item in results
        ]
        audit_event("retrieval.query", tenant_id, item_count=len(results))
        return QueryResponse(
            answer=build_grounded_answer(payload.question, results),
            grounded=bool(results), citations=citations,
            retrieval_method=request.app.state.store.retrieval_method,
        )

    @api.post("/v1/evaluate", response_model=EvaluationResponse, tags=["evaluation"])
    def evaluate(
        payload: EvaluationRequest, request: Request,
        tenant_id: str = Depends(resolve_tenant),
    ) -> EvaluationResponse:
        metrics = evaluate_retrieval(
            [case.model_dump() for case in payload.cases],
            lambda question, k: retrieve(question, k, request, tenant_id),
            payload.top_k,
        )
        audit_event("retrieval.evaluate", tenant_id, item_count=len(payload.cases))
        return EvaluationResponse(**metrics)

    @api.get("/metrics", include_in_schema=False, tags=["service"])
    def metrics(
        request: Request,
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token"),
    ) -> Response:
        expected = request.app.state.settings.metrics_token
        if not expected:
            raise HTTPException(status_code=404, detail="Not found.")
        supplied = x_metrics_token
        if authorization and authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        if not supplied or not hmac.compare_digest(
            hashlib.sha256(supplied.encode("utf-8")).digest(),
            hashlib.sha256(expected.encode("utf-8")).digest(),
        ):
            raise HTTPException(status_code=401, detail="Invalid metrics credential.")
        body, content_type = metrics_response()
        return Response(content=body, media_type=content_type)

    return api


app = create_app()
