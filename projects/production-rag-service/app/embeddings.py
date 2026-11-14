"""Local multilingual embedding generation using FastEmbed/ONNX Runtime."""

from __future__ import annotations

from collections.abc import Iterable

from .retrieval import normalize_text


class FastEmbedder:
    """CPU-friendly multilingual sentence embeddings for Persian and English text."""

    def __init__(self, model_name: str, cache_dir: str):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def _encode(self, texts: Iterable[str]) -> list[list[float]]:
        normalized = [normalize_text(text) for text in texts]
        if not normalized:
            return []
        return [[float(value) for value in vector] for vector in self.model.embed(normalized)]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        vectors = self._encode([text])
        if not vectors:
            raise ValueError("Cannot embed an empty query.")
        return vectors[0]
