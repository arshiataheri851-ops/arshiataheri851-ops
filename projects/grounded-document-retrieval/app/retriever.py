from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class DocumentChunk:
    source: str
    text: str


class DocumentRetriever:
    def __init__(self, documents_dir: Path) -> None:
        self.documents_dir = documents_dir
        self.chunks: list[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            strip_accents="unicode",
        )
        self.matrix = None
        self._load_documents()

    def _load_documents(self) -> None:
        for path in sorted(self.documents_dir.glob("*.txt")):
            content = path.read_text(encoding="utf-8")
            for paragraph in content.split("\n\n"):
                cleaned = " ".join(paragraph.split())
                if cleaned:
                    self.chunks.append(DocumentChunk(source=path.name, text=cleaned))

        if self.chunks:
            self.matrix = self.vectorizer.fit_transform(
                [chunk.text for chunk in self.chunks]
            )

    def search(self, query: str, top_k: int = 3) -> list[dict[str, str | float]]:
        if self.matrix is None:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        ranked_indices = scores.argsort()[::-1][:top_k]

        results = []
        for index in ranked_indices:
            score = float(scores[index])
            if score <= 0:
                continue
            chunk = self.chunks[int(index)]
            results.append(
                {"source": chunk.source, "excerpt": chunk.text, "score": score}
            )
        return results
