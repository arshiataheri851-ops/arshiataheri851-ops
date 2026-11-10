from app.evaluation import evaluate_retrieval


def test_hit_rate_and_mrr():
    corpus = {
        "first": [{"document_id": "wrong"}, {"document_id": "expected"}],
        "second": [{"document_id": "expected"}],
    }
    metrics = evaluate_retrieval([
        {"question": "first", "expected_document_id": "expected"},
        {"question": "second", "expected_document_id": "expected"},
    ], lambda question, _: corpus[question], 3)
    assert metrics["hit_rate_at_k"] == 1.0
    assert metrics["mean_reciprocal_rank"] == 0.75
