from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import Settings, get_settings
from apps.api.app.main import app
from apps.api.app.services.evaluation import run_gold_evaluation
from apps.api.app.services.review_store import get_review_store


def test_gold_evaluation_matches_all_seeded_relations_and_safety_labels() -> None:
    report = run_gold_evaluation(Settings(_env_file=None, demo_mode=True))

    assert report.total_cases == 8
    assert report.exact_matches == 8
    assert report.relation_accuracy == 1
    assert report.actionable_precision == 1
    assert report.citation_coverage == 1
    assert report.hard_negative_false_positives == 0
    results = {item.id: item for item in report.cases}
    assert results["async-payment-stale-doc"].actual_relation == "stale_documentation"
    assert results["disabled-flag-ambiguous"].actual_relation == "ambiguous"
    assert results["rename-only"].actual_relation == "supports"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'feedback.db'}")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    test_client = TestClient(app)
    yield test_client
    get_review_store().connection.close()
    get_review_store.cache_clear()
    get_settings.cache_clear()


def test_evaluation_api_is_labelled_and_schema_complete(client: TestClient) -> None:
    response = client.get("/api/evaluations/gold")

    assert response.status_code == 200
    assert response.json()["provenance"]["label"].startswith("SEEDED EVALUATION")
    assert len(response.json()["cases"]) == 8


def test_reviewer_feedback_is_durable_and_evidence_linked(client: TestClient) -> None:
    alert = client.get("/api/alerts").json()[0]

    response = client.post(
        f"/api/alerts/{alert['id']}/feedback",
        json={
            "actor_id": "evaluation-reviewer",
            "verdict": "false_positive",
            "comment": "The rollout flag evidence needs review.",
        },
    )
    listing = client.get(f"/api/alerts/{alert['id']}/feedback")

    assert response.status_code == 200
    assert response.json()["evidence_ids"] == alert["classification"]["evidence_ids"]
    assert listing.status_code == 200
    assert listing.json()[0]["actor_id"] == "evaluation-reviewer"
    assert listing.json()[0]["verdict"] == "false_positive"
