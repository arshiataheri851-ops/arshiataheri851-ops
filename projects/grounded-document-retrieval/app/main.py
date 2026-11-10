from pathlib import Path
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.retriever import DocumentRetriever


class SearchRequest(BaseModel):
    query: Annotated[str, Field(min_length=2, max_length=500)]
    top_k: Annotated[int, Field(ge=1, le=10)] = 3


class SearchResult(BaseModel):
    source: str
    excerpt: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    count: int


def create_app(retriever: DocumentRetriever | None = None) -> FastAPI:
    app = FastAPI(
        title="Grounded Document Retrieval API",
        description="Source-aware lexical retrieval for local text documents.",
        version="0.1.0",
    )
    search_engine = retriever or DocumentRetriever(
        Path(__file__).resolve().parents[1] / "data" / "docs"
    )

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "indexed_chunks": len(search_engine.chunks)}

    @app.post("/search", response_model=SearchResponse)
    def search(payload: SearchRequest) -> SearchResponse:
        results = search_engine.search(payload.query, payload.top_k)
        return SearchResponse(
            query=payload.query,
            results=[SearchResult(**result) for result in results],
            count=len(results),
        )

    return app


app = create_app()
