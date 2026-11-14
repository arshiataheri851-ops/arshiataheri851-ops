"""Local multilingual text embeddings for AtlasRAG."""

from __future__ import annotations

from collections.abc import Iterable


class FastEmbedder:
    """CPU-friendly ONNX embeddings; document/query prefixes follow the E5 convention."""

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        cache_dir: str | None = None,
    ) -> None:
        from fastembed import TextEmbedding

        kwargs = {"model_name": model_name}
        if cache_dir:
            kwargs["cache_dir"] = cache_dir
        self.model = TextEmbedding(**kwargs)

    @staticmethod
    def _to_vectors(items: Iterable[object]) -> list[list[float]]:
        return [[float(value) for value in item] for item in items]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._to_vectors(
            self.model.embed([f"passage: {text}" for text in texts], batch_size=32)
        )

    def embed_query(self, query: str) -> list[float]:
        vectors = self._to_vectors(self.model.embed([f"query: {query}"], batch_size=1))
        if not vectors:
            raise RuntimeError("Embedding model returned no query vector.")
        return vectors[0]
