from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.services.evidence import EvidenceRegistry


def test_alert_api_returns_complete_grounded_demo_contract() -> None:
    response = TestClient(app).get("/api/alerts")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["status"] == "applied"
    assert alert["classification"]["relationship"] == "stale_documentation"
    assert alert["confidence"] == alert["classification"]["confidence"]
    assert alert["provenance"]["mode"] == "demo_fixture"
    assert alert["provenance"]["inference_mode"] == "demo_fixture_rules"
    assert alert["existing_claim"]["evidence_ids"]
    assert alert["implementation_claim"]["evidence_ids"]
    assert alert["document_evidence"]
    assert alert["implementation_evidence"]
    assert alert["explanations"]["pm"]["what_changed"]
    assert alert["explanations"]["developer"]["technical_change"]
    assert alert["proposed_canonical_statement"]
    assert alert["patch"]["operations"][0]["original_text"]
    assert alert["patch"]["operations"][0]["replacement_text"]


def test_alert_detail_is_stable_and_unknown_alert_is_404() -> None:
    client = TestClient(app)
    first = client.get("/api/alerts").json()[0]
    second = client.get("/api/alerts").json()[0]

    assert first["id"] == second["id"]
    assert client.get(f"/api/alerts/{first['id']}").status_code == 200
    assert client.get("/api/alerts/not-found").status_code == 404


def test_every_alert_claim_and_output_reference_is_registered() -> None:
    alert = TestClient(app).get("/api/alerts").json()[0]
    evidence = alert["document_evidence"] + alert["implementation_evidence"]
    from apps.api.app.domain.schemas import EvidenceSpan

    registry = EvidenceRegistry(EvidenceSpan.model_validate(item) for item in evidence)
    referenced = (
        alert["existing_claim"]["evidence_ids"]
        + alert["implementation_claim"]["evidence_ids"]
        + alert["classification"]["evidence_ids"]
        + alert["explanations"]["evidence_ids"]
        + alert["patch"]["evidence_ids"]
    )
    registry.validate(referenced)
