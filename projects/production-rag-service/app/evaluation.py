from collections.abc import Callable


def evaluate_retrieval(cases: list[dict], retrieve: Callable[[str, int], list[dict]],
                       top_k: int) -> dict[str, float | int]:
    hits = 0
    reciprocal_ranks: list[float] = []
    for case in cases:
        results = retrieve(case["question"], top_k)
        rank = next((i for i, item in enumerate(results, start=1)
                     if item["document_id"] == case["expected_document_id"]), None)
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
    total = len(cases)
    return {
        "cases": total,
        "hit_rate_at_k": hits / total if total else 0.0,
        "mean_reciprocal_rank": sum(reciprocal_ranks) / total if total else 0.0,
    }
