from app.retrieval import BM25Retriever, tokenize


def test_tokenizer_supports_persian_and_english():
    assert tokenize("مدل زبان Python") == ["مدل", "زبان", "python"]


def test_bm25_ranks_relevant_chunk_first():
    docs = [
        {"chunk_id": "a", "document_id": "a", "text": "Database indexing improves query performance."},
        {"chunk_id": "b", "document_id": "b", "text": "A neural network learns representations from data."},
    ]
    result = BM25Retriever().search("database query indexing", docs, 2)
    assert result[0]["document_id"] == "a"
    assert result[0]["score"] > 0


def test_no_overlap_returns_no_results():
    assert BM25Retriever().search("quantum", [{"chunk_id": "x", "text": "database"}], 5) == []
