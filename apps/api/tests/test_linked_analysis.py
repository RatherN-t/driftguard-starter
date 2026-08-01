from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import get_settings
from apps.api.app.main import app
from apps.api.app.services.active_analysis import get_active_analysis_store
from apps.api.app.services.review_store import get_review_store
from apps.api.app.services.writeback import DEMO_OUTPUT

DEMO_REQUEST = {
    "document_url": "demo://architecture_doc.md",
    "repository_url": "https://github.com/example/driftguard-demo",
    "pull_request_url": "https://github.com/example/driftguard-demo/pull/7",
    "use_demo_transcript": True,
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'analysis.db'}")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    get_active_analysis_store().clear()
    if DEMO_OUTPUT.is_file():
        DEMO_OUTPUT.unlink()
    test_client = TestClient(app)
    yield test_client
    if DEMO_OUTPUT.is_file():
        DEMO_OUTPUT.unlink()
    get_active_analysis_store().clear()
    get_review_store().connection.close()
    get_review_store.cache_clear()
    get_settings.cache_clear()


def test_current_analysis_names_exact_document_repository_pr_and_transcript(
    client: TestClient,
) -> None:
    response = client.get("/api/analysis/current")

    assert response.status_code == 200
    payload = response.json()
    sources = {item["role"]: item for item in payload["sources"]}
    assert sources["document"]["uri"] == "demo://architecture_doc.md"
    assert sources["document"]["source_id"] == "demo/architecture_doc.md"
    assert sources["repository"]["uri"] == "https://github.com/example/driftguard-demo"
    assert sources["pull_request"]["uri"].endswith("/pull/7")
    assert "payment_api.py" in " ".join(sources["pull_request"]["details"])
    assert sources["transcript"]["uri"] == "demo://meeting_transcript.txt"
    assert payload["document_change"]["target"].endswith(
        "demo_architecture_doc.approved.md"
    )
    assert "calls the payment provider synchronously" in payload["document_change"][
        "before_content"
    ]
    assert "returns HTTP 202" in payload["document_change"]["proposed_content"]


def test_linked_demo_analysis_and_custom_transcript_are_accepted(
    client: TestClient,
) -> None:
    request = {
        **DEMO_REQUEST,
        "use_demo_transcript": False,
        "transcript_text": "[00:00] Alex: We need to review checkout behavior.",
    }
    response = client.post("/api/analysis/run", json=request)

    assert response.status_code == 200
    payload = response.json()
    assert payload["alert"]["classification"]["relationship"] == "stale_documentation"
    assert payload["transcript"]["transcript"]["segments"][0]["speaker"] == "Alex"
    assert payload["transcript"]["decisions"]["decisions"] == []
    assert "configure MISTRAL_API_KEY" in payload["transcript"]["provenance"]["label"]


def test_repository_and_pr_must_match(client: TestClient) -> None:
    response = client.post(
        "/api/analysis/run",
        json={**DEMO_REQUEST, "repository_url": "https://github.com/example/other"},
    )

    assert response.status_code == 422
    assert "same repository" in response.json()["detail"]


def test_live_google_link_fails_clearly_without_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/analysis/run",
        json={
            **DEMO_REQUEST,
            "document_url": "https://docs.google.com/document/d/demo-document-id/edit",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Google Docs linking requires GOOGLE_SERVICE_ACCOUNT_FILE"
    )


def test_applied_document_view_shows_actual_local_copy(client: TestClient) -> None:
    result = client.post("/api/analysis/run", json=DEMO_REQUEST).json()
    alert_id = result["alert"]["id"]
    change = client.get(f"/api/alerts/{alert_id}/document-change")

    assert result["alert"]["status"] == "applied"
    assert change.status_code == 200
    assert change.json()["applied_content"] == change.json()["proposed_content"]
    assert "returns HTTP 202" in change.json()["applied_content"]
