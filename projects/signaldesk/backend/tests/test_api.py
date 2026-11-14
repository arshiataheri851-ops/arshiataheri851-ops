from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_list_has_seed_records():
    response = client.get("/tickets")
    assert response.status_code == 200
    assert any(ticket["id"] == "SD-1048" for ticket in response.json())


def test_summary_counts_match_seeded_records():
    result = client.get("/analytics/summary").json()
    assert result["total"] >= 5
    assert "at_risk" in result


def test_sla_risk_filter_returns_only_at_risk_records():
    response = client.get("/tickets", params={"sla_state": "at_risk"})
    assert response.status_code == 200
    assert all(ticket["sla_state"] == "at_risk" for ticket in response.json())


def test_invalid_sla_filter_is_rejected():
    response = client.get("/tickets", params={"sla_state": "urgent"})
    assert response.status_code == 422


def test_ticket_creation_assignment_status_and_audit_history():
    ticket_id = f"SD-{uuid4().hex[:10]}"
    created = client.post("/tickets", json={
        "id": ticket_id,
        "title": "Customer cannot access workspace",
        "queue": "Accounts",
        "account_tier": "Growth",
        "priority": "High",
        "due_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    })
    assert created.status_code == 201

    assigned = client.patch(f"/tickets/{ticket_id}/assign", json={"assignee": "Support Agent"})
    assert assigned.status_code == 200
    assert assigned.json()["assignee"] == "Support Agent"

    changed = client.patch(f"/tickets/{ticket_id}/status", json={"status": "in_progress"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "in_progress"

    events = client.get(f"/tickets/{ticket_id}/events")
    assert events.status_code == 200
    assert {event["event_type"] for event in events.json()} >= {"created", "assigned", "status_changed"}


def test_resolved_ticket_cannot_be_assigned():
    ticket_id = f"SD-{uuid4().hex[:10]}"
    created = client.post("/tickets", json={
        "id": ticket_id,
        "title": "Refund status request",
        "queue": "Billing",
        "priority": "Low",
        "due_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    })
    assert created.status_code == 201
    assert client.patch(f"/tickets/{ticket_id}/status", json={"status": "resolved"}).status_code == 200
    assert client.patch(f"/tickets/{ticket_id}/assign", json={"assignee": "Support Agent"}).status_code == 409

def test_readiness_checks_database():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
