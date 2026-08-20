"""Acceptance tests for Layer 6: FastAPI REST API Layer."""

import pytest
from fastapi.testclient import TestClient
from layer6_api.main import app
from layer6_api.routes import review


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_review_endpoint_rejects_empty_code(client):
    resp = client.post("/review", json={"code": "   "})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_review_endpoint_rejects_oversized_code(client):
    huge_code = "x = 1\n" * 20000  # > 50,000 chars
    resp = client.post("/review", json={"code": huge_code})
    assert resp.status_code == 413
    assert "limit" in resp.json()["detail"].lower()


def test_review_endpoint_happy_path(client, monkeypatch):
    # Mock run_review for instant deterministic response
    mock_findings = [
        {
            "principle": "SRP",
            "evidence_chunk_id": "tool:ast",
            "severity": "high",
            "location": "GodClass",
            "explanation": "Violates Single Responsibility Principle.",
            "suggested_fix": "Decompose into smaller components.",
        }
    ]

    def mock_run_review(code: str):
        return {
            "findings": mock_findings,
            "report_markdown": "# Code Review Report\n1 findings",
            "iteration_count": 1,
            "state": {},
        }

    monkeypatch.setattr("layer6_api.routes.review.run_review", mock_run_review)

    resp = client.post("/review", json={"code": "class GodClass: pass"})
    assert resp.status_code == 200

    data = resp.json()
    assert "findings" in data
    assert len(data["findings"]) == 1
    assert data["findings"][0]["principle"] == "SRP"
    assert data["iteration_count"] == 1
    assert "X-Session-Id" in resp.headers
    session_id = resp.headers["X-Session-Id"]
    assert len(session_id) > 10


def test_hitl_decision_accept(client, monkeypatch):
    # Set up session in _SESSIONS
    session_id = "test-session-123"
    review._SESSIONS[session_id] = {
        "findings": [{"principle": "SRP"}],
        "report_markdown": "report",
        "iteration_count": 1,
    }

    resp = client.post(
        f"/review/{session_id}/decision",
        json={"finding_index": 0, "decision": "accept"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["decision"] == "accept"


def test_hitl_decision_requires_edited_text_for_edit(client):
    session_id = "test-session-edit"
    review._SESSIONS[session_id] = {
        "findings": [{"principle": "SRP"}],
        "report_markdown": "report",
        "iteration_count": 1,
    }

    resp = client.post(
        f"/review/{session_id}/decision",
        json={"finding_index": 0, "decision": "edit", "edited_text": ""},
    )
    assert resp.status_code == 400
    assert "edited_text required" in resp.json()["detail"]


def test_hitl_decision_unknown_session_404(client):
    resp = client.post(
        "/review/non-existent-session-id/decision",
        json={"finding_index": 0, "decision": "reject"},
    )
    assert resp.status_code == 404
