"""Transparent content-aware ranking with weighted implicit feedback."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.store import EVENT_WEIGHTS, EventStore


DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "item_id": "course-python",
        "title": "Python Fundamentals",
        "category": "programming",
        "tags": ["python", "beginner", "coding"],
    },
    {
        "item_id": "course-django",
        "title": "Django API Engineering",
        "category": "backend",
        "tags": ["django", "api", "python"],
    },
    {
        "item_id": "course-sql",
        "title": "Practical SQL",
        "category": "data",
        "tags": ["sql", "database", "analytics"],
    },
    {
        "item_id": "course-ml",
        "title": "Machine Learning Foundations",
        "category": "ai",
        "tags": ["machine-learning", "python", "statistics"],
    },
    {
        "item_id": "course-rag",
        "title": "Building Retrieval-Augmented Generation",
        "category": "ai",
        "tags": ["llm", "rag", "python"],
    },
    {
        "item_id": "course-cloud",
        "title": "Cloud-Native Service Design",
        "category": "backend",
        "tags": ["docker", "cloud", "deployment"],
    },
]


class RecommendationService:
    def __init__(
        self,
        store: EventStore,
        catalog: list[dict[str, Any]] | None = None,
    ) -> None:
        self.store = store
        self.catalog = [dict(item) for item in (catalog or DEFAULT_CATALOG)]
        self._items = {item["item_id"]: item for item in self.catalog}
        if len(self._items) != len(self.catalog):
            raise ValueError("Catalog item IDs must be unique")
        for item in self.catalog:
            if not {"item_id", "title", "category", "tags"} <= set(item):
                raise ValueError("Every catalog item needs item_id, title, category, and tags")
            if not isinstance(item["tags"], list):
                raise ValueError("Catalog tags must be lists")

    def record_event(self, user_id: str, item_id: str, event_type: str) -> dict[str, Any]:
        if item_id not in self._items:
            raise KeyError(f"Catalog item '{item_id}' not found")
        return self.store.record_event(user_id, item_id, event_type)

    def recommend(self, user_id: str, limit: int = 5) -> dict[str, Any]:
        if not user_id.strip():
            raise ValueError("user_id cannot be empty")
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")

        history = self.store.user_events(user_id)
        seen = self.store.seen_items(user_id)
        popularity = self.store.item_popularity()
        candidates = [item for item in self.catalog if item["item_id"] not in seen]

        if not history:
            ranked = sorted(
                candidates,
                key=lambda item: (-popularity.get(item["item_id"], 0.0), item["title"].casefold()),
            )
            results = [
                self._result(item, popularity.get(item["item_id"], 0.0), "Popular with users")
                for item in ranked[:limit]
            ]
            return {
                "user_id": user_id,
                "strategy": "popular_fallback",
                "recommendations": results,
            }

        category_affinity: Counter[str] = Counter()
        tag_affinity: Counter[str] = Counter()
        for event in history:
            item = self._items.get(event["item_id"])
            if item is None:
                continue
            weight = EVENT_WEIGHTS[event["event_type"]]
            category_affinity[item["category"]] += weight
            for tag in item["tags"]:
                tag_affinity[tag] += weight

        ranked_scores: list[tuple[float, dict[str, Any], str]] = []
        for item in candidates:
            category_score = category_affinity[item["category"]]
            matching_tags = [
                tag for tag in item["tags"] if tag in tag_affinity
            ]
            tag_score = sum(tag_affinity[tag] for tag in matching_tags)
            popularity_score = popularity.get(item["item_id"], 0.0)
            score = (2.0 * category_score) + (0.5 * tag_score) + (0.1 * popularity_score)

            if category_score:
                reason = f"Matches your interest in {item['category']}"
            elif matching_tags:
                reason = f"Shares your interests in {', '.join(sorted(matching_tags))}"
            else:
                reason = "Popular with users"
            ranked_scores.append((score, item, reason))

        ranked_scores.sort(key=lambda row: (-row[0], row[1]["title"].casefold()))
        return {
            "user_id": user_id,
            "strategy": "personalized_implicit_feedback",
            "recommendations": [
                self._result(item, score, reason)
                for score, item, reason in ranked_scores[:limit]
            ],
        }

    @staticmethod
    def _result(item: dict[str, Any], score: float, reason: str) -> dict[str, Any]:
        return {
            "item_id": item["item_id"],
            "title": item["title"],
            "category": item["category"],
            "score": round(score, 6),
            "reason": reason,
        }
