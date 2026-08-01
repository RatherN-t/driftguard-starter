from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import Settings, get_settings
from apps.api.app.main import app
from apps.api.app.services.demo_pipeline import build_demo_alert
from apps.api.app.services.notifications import NotificationService, NotificationUnavailable
from apps.api.app.services.review_store import ReviewStore, get_review_store


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'notify.db'}")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    test_client = TestClient(app)
    yield test_client
    get_review_store().connection.close()
    get_review_store.cache_clear()
    get_settings.cache_clear()


def test_preview_is_available_without_email_credentials_and_contains_no_code(
    client: TestClient,
) -> None:
    alert = client.get("/api/alerts").json()[0]

    response = client.get(f"/api/alerts/{alert['id']}/email/preview")

    assert response.status_code == 200
    assert response.json()["subject"].startswith("DriftGuard review:")
    assert alert["proposed_canonical_statement"] in response.json()["text"]
    assert "def checkout" not in response.json()["text"]
    assert response.json()["evidence_ids"] == alert["classification"]["evidence_ids"]


def test_api_send_requires_approval_and_smtp_configuration(client: TestClient) -> None:
    alert = client.get("/api/alerts").json()[0]
    before_approval = client.post(
        f"/api/alerts/{alert['id']}/email/send",
        json={"actor_id": "reviewer", "recipients": ["pm@example.test"]},
    )
    client.post(f"/api/alerts/{alert['id']}/approve", json={"actor_id": "reviewer"})
    without_smtp = client.post(
        f"/api/alerts/{alert['id']}/email/send",
        json={"actor_id": "reviewer", "recipients": ["pm@example.test"]},
    )

    assert before_approval.status_code == 409
    assert without_smtp.status_code == 409
    assert "SMTP" in without_smtp.json()["detail"]


def test_injected_smtp_delivery_is_deduplicated(tmp_path: Path) -> None:
    store = ReviewStore(f"sqlite:///{tmp_path / 'smtp.db'}")
    settings = Settings(
        _env_file=None,
        demo_mode=True,
        email_mode="smtp",
        smtp_host="smtp.example.test",
        smtp_username="user",
        smtp_password="safe-test-placeholder",
        smtp_from="driftguard@example.test",
    )
    alert = build_demo_alert(settings)
    store.transition(alert, action="approve", actor_id="reviewer")
    sender = FakeSender()
    service = NotificationService(settings, store, email_client=sender)

    result = service.send(
        alert, recipients=["pm@example.test"], actor_id="reviewer"
    )

    assert result.status == "sent"
    assert len(sender.messages) == 1
    with pytest.raises(NotificationUnavailable, match="already sent"):
        service.send(alert, recipients=["pm@example.test"], actor_id="reviewer")
    assert len(sender.messages) == 1


def test_failed_delivery_can_be_retried(tmp_path: Path) -> None:
    store = ReviewStore(f"sqlite:///{tmp_path / 'retry.db'}")
    settings = Settings(
        _env_file=None,
        demo_mode=True,
        email_mode="smtp",
        smtp_host="smtp.example.test",
        smtp_username="user",
        smtp_password="safe-test-placeholder",
        smtp_from="driftguard@example.test",
    )
    alert = build_demo_alert(settings)
    store.transition(alert, action="approve", actor_id="reviewer")
    sender = FailOnceSender()
    service = NotificationService(settings, store, email_client=sender)

    with pytest.raises(NotificationUnavailable, match="delivery failed"):
        service.send(alert, recipients=["pm@example.test"], actor_id="reviewer")

    result = service.send(
        alert, recipients=["pm@example.test"], actor_id="reviewer"
    )
    assert result.status == "sent"
    assert sender.attempts == 2


class FakeSender:
    def __init__(self):
        self.messages: list[object] = []

    def send(self, message: object) -> None:
        self.messages.append(message)


class FailOnceSender:
    def __init__(self):
        self.attempts = 0

    def send(self, message: object) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise OSError("simulated SMTP timeout")
