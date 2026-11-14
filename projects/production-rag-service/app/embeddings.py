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

        # FastEmbed does not include multilingual-e5-small in its built-in
        # registry. Register its published ONNX artifact as a 384-dim model
        # before constructing the embedder; avoid duplicate registration.
        if model_name == "intfloat/multilingual-e5-small":
            supported = {
                item["model"] for item in TextEmbedding.list_supported_models()
            }
            if model_name not in supported:
                from fastembed.common.model_description import ModelSource, PoolingType

                TextEmbedding.add_custom_model(
                    model=model_name,
                    pooling=PoolingType.MEAN,
                    normalization=True,
                    sources=ModelSource(hf=model_name),
                    dim=384,
                    model_file="onnx/model.onnx",
                )

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
