import pytest

from app.store import FeatureStore


def test_typed_write_versioning_and_read():
    store = FeatureStore(clock=lambda: 100.0)
    store.create_group("customer", {"age": "integer", "active": "boolean"})
    store.write("customer", "u-1", {"age": 28, "active": True})
    first = store.get("customer", "u-1")
    assert first["features"]["age"]["version"] == 1
    assert first["features"]["active"]["value"] is True

    store.write("customer", "u-1", {"age": 29})
    second = store.get("customer", "u-1")
    assert second["features"]["age"]["version"] == 2
    assert second["features"]["age"]["value"] == 29


def test_ttl_marks_stale_features():
    now = {"value": 10.0}
    store = FeatureStore(clock=lambda: now["value"])
    store.create_group("risk", {"score": "number"}, ttl_seconds=5)
    store.write("risk", "account-1", {"score": 0.83})
    assert store.get("risk", "account-1")["is_stale"] is False
    now["value"] = 16.0
    result = store.get("risk", "account-1")
    assert result["is_stale"] is True
    assert result["features"]["score"]["stale"] is True


def test_schema_validation_and_missing_group():
    store = FeatureStore()
    store.create_group("profile", {"age": "integer"})
    with pytest.raises(ValueError, match="must have type integer"):
        store.write("profile", "u-1", {"age": True})
    with pytest.raises(ValueError, match="Undeclared"):
        store.write("profile", "u-1", {"unknown": 2})
    with pytest.raises(KeyError, match="not found"):
        store.get("missing", "u-1")


def test_non_finite_numbers_are_rejected():
    store = FeatureStore()
    store.create_group("metrics", {"value": "number"})
    with pytest.raises(ValueError, match="must have type number"):
        store.write("metrics", "entity-1", {"value": float("nan")})


def test_batch_rejects_duplicate_and_oversized_requests():
    store = FeatureStore()
    store.create_group("profile", {"age": "integer"})
    with pytest.raises(ValueError, match="unique"):
        store.get_many("profile", ["a", "a"])
    with pytest.raises(ValueError, match="500"):
        store.get_many("profile", [str(index) for index in range(501)])
