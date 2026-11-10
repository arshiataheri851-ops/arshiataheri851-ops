from fastapi.testclient import TestClient

from app.main import create_app
from app.store import FeatureStore


def test_feature_group_write_and_read_api():
    client = TestClient(create_app(FeatureStore(clock=lambda: 100.0)))
    group = client.post(
        "/feature-groups",
        json={
            "group_name": "customer_profile",
            "schema": {"age": "integer", "active": "boolean"},
            "ttl_seconds": 60,
        },
    )
    assert group.status_code == 201

    write = client.put(
        "/feature-groups/customer_profile/entities/u-1",
        json={"entity_id": "u-1", "features": {"age": 25, "active": True}},
    )
    assert write.status_code == 200

    read = client.get("/feature-groups/customer_profile/entities/u-1")
    assert read.status_code == 200
    assert read.json()["features"]["age"]["value"] == 25


def test_invalid_feature_value_returns_422():
    client = TestClient(create_app())
    client.post(
        "/feature-groups",
        json={"group_name": "scores", "schema": {"score": "number"}},
    )
    response = client.put(
        "/feature-groups/scores/entities/u-1",
        json={"entity_id": "u-1", "features": {"score": "not-a-number"}},
    )
    assert response.status_code == 422


def test_batch_get_endpoint():
    client = TestClient(create_app())
    client.post(
        "/feature-groups",
        json={"group_name": "profile", "schema": {"age": "integer"}},
    )
    client.put(
        "/feature-groups/profile/entities/u-1",
        json={"entity_id": "u-1", "features": {"age": 30}},
    )
    response = client.post(
        "/feature-groups/profile/entities:batchGet",
        json={"entity_ids": ["u-1", "u-2"]},
    )
    assert response.status_code == 200
    assert response.json()[0]["features"]["age"]["value"] == 30
    assert response.json()[1]["features"] == {}
