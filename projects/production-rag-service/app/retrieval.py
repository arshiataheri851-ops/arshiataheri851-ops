import math
import re
from collections import Counter
from typing import Any

_TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


class BM25Retriever:
    """Dependency-light BM25 ranker over persisted text chunks."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        query_terms = tokenize(query)
        if not query_terms or not documents:
            return []
        tokenized = [tokenize(doc["text"]) for doc in documents]
        lengths = [len(tokens) for tokens in tokenized]
        avg_len = sum(lengths) / len(lengths) if lengths else 0.0
        doc_freq: Counter[str] = Counter()
        term_freqs = [Counter(tokens) for tokens in tokenized]
        for terms in term_freqs:
            doc_freq.update(terms.keys())
        n_docs = len(documents)
        scored: list[dict[str, Any]] = []
        for doc, tf_map, length in zip(documents, term_freqs, lengths, strict=True):
            score = 0.0
            for term in query_terms:
                tf = tf_map.get(term, 0)
                if not tf:
                    continue
                df = doc_freq[term]
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                norm = tf + self.k1 * (1 - self.b + self.b * length / (avg_len or 1))
                score += idf * (tf * (self.k1 + 1)) / norm
            if score > 0:
                scored.append({**doc, "score": score})
        return sorted(scored, key=lambda item: (-item["score"], item["chunk_id"]))[:top_k]
