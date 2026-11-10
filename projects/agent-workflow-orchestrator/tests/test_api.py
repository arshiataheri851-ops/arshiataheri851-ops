def test_create_and_read_workflow(client):
    payload = {
        "workflow_id": "api-demo", "title": "API demo",
        "tasks": [
            {"task_id": "plan", "role": "planner", "description": "Create plan"},
            {"task_id": "build", "role": "developer", "description": "Build it",
             "depends_on": ["plan"]},
        ],
    }
    created = client.post("/v1/workflows", json=payload)
    assert created.status_code == 201
    assert created.json()["tasks"]["plan"]["status"] == "ready"
    assert created.json()["tasks"]["build"]["status"] == "pending"
    fetched = client.get("/v1/workflows/api-demo")
    assert fetched.status_code == 200


def test_api_approval_claim_complete_and_audit(client):
    payload = {
        "workflow_id": "approval-demo", "title": "Approval",
        "tasks": [
            {"task_id": "draft", "role": "writer", "description": "Draft"},
            {"task_id": "publish", "role": "publisher", "description": "Publish",
             "depends_on": ["draft"], "requires_approval": True},
        ],
    }
    assert client.post("/v1/workflows", json=payload).status_code == 201
    assert client.post(
        "/v1/workflows/approval-demo/tasks/draft/claim", json={"actor": "worker"}
    ).status_code == 200
    assert client.post(
        "/v1/workflows/approval-demo/tasks/draft/complete",
        json={"actor": "worker", "result": {"draft_id": "d-1"}},
    ).status_code == 200
    waiting = client.get("/v1/workflows/approval-demo").json()
    assert waiting["tasks"]["publish"]["status"] == "awaiting_approval"
    approved = client.post(
        "/v1/workflows/approval-demo/tasks/publish/approve",
        json={"actor": "human"},
    )
    assert approved.status_code == 200
    assert approved.json()["tasks"]["publish"]["approved_by"] == "human"
    audit = client.get("/v1/workflows/approval-demo/audit")
    assert audit.status_code == 200
    assert any(item["event_type"] == "approval_granted" for item in audit.json())


def test_unknown_workflow_returns_404(client):
    assert client.get("/v1/workflows/missing").status_code == 404


def test_invalid_dependency_returns_422(client):
    response = client.post("/v1/workflows", json={
        "workflow_id": "bad", "title": "Bad",
        "tasks": [{"task_id": "a", "role": "worker", "description": "A",
                   "depends_on": ["absent"]}],
    })
    assert response.status_code == 422
