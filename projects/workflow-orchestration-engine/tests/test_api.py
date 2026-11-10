from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_validate_and_execute_endpoints():
    payload = {
        "steps": [
            {"name": "total", "action": "sum", "params": {"values": [2, 3, 4]}},
            {
                "name": "copy",
                "action": "copy_dependency",
                "depends_on": ["total"],
                "params": {"dependency": "total"},
            },
        ]
    }
    validation = client.post("/workflows/validate", json=payload)
    assert validation.status_code == 200
    assert validation.json()["execution_order"] == ["total", "copy"]

    execution = client.post("/workflows/execute", json=payload)
    assert execution.status_code == 200
    assert execution.json()["steps"][1]["output"] == 9


def test_invalid_graph_returns_422():
    response = client.post(
        "/workflows/validate",
        json={"steps": [{"name": "x", "action": "sum", "depends_on": ["y"]}]},
    )
    assert response.status_code == 422
