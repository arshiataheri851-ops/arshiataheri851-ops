import pytest

from app.recommender import DEFAULT_CATALOG, RecommendationService
from app.store import EventStore


def test_cold_start_uses_weighted_popularity_fallback():
    store = EventStore(clock=lambda: 100.0)
    service = RecommendationService(store)
    service.record_event("buyer-1", "course-ml", "purchase")
    service.record_event("viewer-2", "course-python", "view")

    result = service.recommend("new-user", limit=3)

    assert result["strategy"] == "popular_fallback"
    assert result["recommendations"][0]["item_id"] == "course-ml"
    assert result["recommendations"][0]["reason"] == "Popular with users"


def test_personalized_ranking_suppresses_seen_items_and_explains_results():
    store = EventStore(clock=lambda: 100.0)
    service = RecommendationService(store)
    service.record_event("user-1", "course-python", "purchase")

    result = service.recommend("user-1", limit=5)

    assert result["strategy"] == "personalized_implicit_feedback"
    returned_ids = {item["item_id"] for item in result["recommendations"]}
    assert "course-python" not in returned_ids
    assert result["recommendations"]
    assert all(item["reason"] for item in result["recommendations"])
    assert any("python" in item["reason"].lower() for item in result["recommendations"])


def test_invalid_limits_and_unknown_catalog_items_are_rejected():
    service = RecommendationService(EventStore())
    with pytest.raises(ValueError, match="between 1 and 50"):
        service.recommend("user-1", limit=0)
    with pytest.raises(KeyError, match="not found"):
        service.record_event("user-1", "missing-item", "view")


def test_catalog_ids_must_be_unique():
    store = EventStore()
    duplicate_catalog = [DEFAULT_CATALOG[0], DEFAULT_CATALOG[0]]
    with pytest.raises(ValueError, match="unique"):
        RecommendationService(store, duplicate_catalog)
