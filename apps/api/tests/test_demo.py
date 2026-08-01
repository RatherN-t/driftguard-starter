from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_demo_loader_labels_fixture_data() -> None:
    response = TestClient(app).post("/api/demo/load")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"] == {
        "mode": "demo_fixture",
        "is_demo": True,
        "label": "DEMO DATA - local fixtures, not live connector results",
    }
    assert payload["architecture_document"]
    assert payload["product_requirements"]
    assert payload["meeting_transcript"]
    assert payload["pr"]
    assert payload["expected_alert"]


def test_demo_loader_is_deterministic() -> None:
    client = TestClient(app)

    first = client.post("/api/demo/load")
    second = client.post("/api/demo/load")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_google_sync_uses_labelled_fixture_in_demo_mode() -> None:
    response = TestClient(app).post("/api/sources/google/sync", json={})

    assert response.status_code == 200
    assert response.json()["provenance"]["mode"] == "demo_fixture"
    assert response.json()["evidence"]
