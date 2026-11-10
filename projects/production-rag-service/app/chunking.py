from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str


def split_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[TextChunk]:
    """Split text on word boundaries while retaining configurable overlap."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size - 1")
    words = re.findall(r"\\S+", text.strip())
    if not words:
        return []
    chunks: list[TextChunk] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(TextChunk(index=len(chunks), text=" ".join(words[start:end])))
        if end == len(words):
            break
        start = end - overlap
    return chunks
