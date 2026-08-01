from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import get_settings
from apps.api.app.main import app
from apps.api.app.services.review_store import get_review_store


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'review.db'}")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    test_client = TestClient(app)
    yield test_client
    get_review_store().connection.close()
    get_review_store.cache_clear()
    get_settings.cache_clear()


def test_alert_is_auto_approved_and_applied_with_no_human_action(client: TestClient) -> None:
    alert = client.get("/api/alerts").json()[0]

    assert alert["status"] == "applied"
    audit = client.get(f"/api/alerts/{alert['id']}/audit").json()
    assert [event["event_type"] for event in audit] == ["alert_approved", "patch_applied"]
    approval_event = audit[0]
    assert approval_event["prior_state"] == "pending_review"
    assert approval_event["new_state"] == "approved"
    assert approval_event["actor_id"] == "system:auto-approval"
    assert approval_event["proposed_patch"] == alert["patch"]
    assert approval_event["evidence_ids"] == alert["classification"]["evidence_ids"]


def test_manual_approve_and_reject_are_no_longer_reachable_once_auto_applied(
    client: TestClient,
) -> None:
    alert = client.get("/api/alerts").json()[0]

    approve = client.post(
        f"/api/alerts/{alert['id']}/approve",
        json={"actor_id": "reviewer"},
    )
    reject = client.post(
        f"/api/alerts/{alert['id']}/reject",
        json={"actor_id": "reviewer", "reason_code": "future_state_documentation"},
    )

    assert approve.status_code == 409
    assert reject.status_code == 409
    assert client.get(f"/api/alerts/{alert['id']}").json()["status"] == "applied"


def test_audit_is_durable_and_demo_reset_restores_pending_state_before_next_fetch(
    client: TestClient,
) -> None:
    alert = client.get("/api/alerts").json()[0]

    audit = client.get(f"/api/alerts/{alert['id']}/audit")
    reset = client.post("/api/demo/reset")

    assert audit.status_code == 200
    assert len(audit.json()) == 2
    assert reset.status_code == 200
    assert client.get(f"/api/alerts/{alert['id']}/audit").json() == []
    assert client.get(f"/api/alerts/{alert['id']}").json()["status"] == "applied"
