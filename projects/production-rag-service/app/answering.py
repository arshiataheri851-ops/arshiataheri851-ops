import re
from typing import Any
from .retrieval import tokenize


def build_grounded_answer(question: str, results: list[dict[str, Any]]) -> str:
    """Return the best evidence sentence; never invent an answer without evidence."""
    if not results:
        return "I could not find supporting evidence in the indexed documents."
    query_terms = set(tokenize(question))
    candidates: list[tuple[float, str]] = []
    for result in results:
        sentences = re.split(r"(?<=[.!?؟])\s+|\n+", result["text"])
        for sentence in sentences:
            words = set(tokenize(sentence))
            if not words:
                continue
            overlap = len(query_terms & words) / max(len(query_terms), 1)
            if overlap:
                candidates.append((overlap + min(result["score"], 5.0) * 0.01, sentence.strip()))
    if not candidates:
        return "Relevant documents were retrieved, but no concise answer sentence could be extracted."
    return max(candidates, key=lambda item: item[0])[1]
