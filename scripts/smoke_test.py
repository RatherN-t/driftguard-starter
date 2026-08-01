import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="driftguard-smoke-") as temp_dir:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(temp_dir) / 'smoke.db'}"
        os.environ["DEMO_MODE"] = "true"
        os.environ["MISTRAL_API_KEY"] = ""
        os.environ["GOOGLE_WRITE_ENABLED"] = "false"
        os.environ["EMAIL_MODE"] = "console"

        from apps.api.app.main import app
        from apps.api.app.services.review_store import get_review_store

        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.post("/api/demo/reset").status_code == 200

        demo = client.post("/api/demo/load")
        assert demo.status_code == 200
        assert demo.json()["provenance"]["mode"] == "demo_fixture"
        assert demo.json()["provenance"]["is_demo"] is True
        assert "synchronously" in demo.json()["architecture_document"]

        current = client.get("/api/analysis/current").json()
        source_roles = {item["role"]: item for item in current["sources"]}
        assert source_roles["document"]["uri"] == "demo://architecture_doc.md"
        assert source_roles["repository"]["uri"] == (
            "https://github.com/example/driftguard-demo"
        )
        assert source_roles["pull_request"]["uri"].endswith("/pull/7")
        assert source_roles["transcript"]["uri"] == "demo://meeting_transcript.txt"
        assert "synchronously" in current["document_change"]["before_content"]
        assert "returns HTTP 202" in current["document_change"]["proposed_content"]

        alert = current["alert"]
        assert alert["status"] == "applied"
        assert alert["classification"]["relationship"] == "stale_documentation"
        known_evidence = {
            item["id"]
            for item in alert["document_evidence"] + alert["implementation_evidence"]
        }
        assert set(alert["classification"]["evidence_ids"]) <= known_evidence

        decisions = client.get("/api/sources/transcript/demo").json()
        assert decisions["decisions"]["decisions"][0]["status"] == "confirmed"
        assert decisions["decisions"]["unresolved_questions"][0]["status"] == "ambiguous"

        evaluation = client.get("/api/evaluations/gold").json()
        assert evaluation["exact_matches"] == evaluation["total_cases"] == 8
        assert evaluation["hard_negative_false_positives"] == 0

        feedback = client.post(
            f"/api/alerts/{alert['id']}/feedback",
            json={"actor_id": "smoke-reviewer", "verdict": "correct"},
        )
        assert feedback.status_code == 200

        preview = client.get(f"/api/alerts/{alert['id']}/email/preview")
        assert preview.status_code == 200
        assert preview.json()["evidence_ids"] == alert["classification"]["evidence_ids"]

        # Human review is disabled: the alert is auto-approved and auto-applied
        # as soon as it is fetched, with no manual approve/apply call needed.
        output_path = Path(current["document_change"]["target"])
        assert output_path.is_file()
        assert "returns HTTP 202" in output_path.read_text(encoding="utf-8")
        applied_change = client.get(
            f"/api/alerts/{alert['id']}/document-change"
        ).json()
        assert applied_change["applied_content"] == applied_change["proposed_content"]

        audit = client.get(f"/api/alerts/{alert['id']}/audit").json()
        assert [item["event_type"] for item in audit] == [
            "alert_approved",
            "patch_applied",
        ]
        assert audit[0]["actor_id"] == "system:auto-approval"

        manual_apply = client.post(
            f"/api/alerts/{alert['id']}/apply",
            json={"actor_id": "smoke-reviewer"},
        )
        assert manual_apply.status_code == 409

        assert client.post("/api/demo/reset").status_code == 200
        assert not output_path.exists()
        assert client.get("/api/analysis/current").json()["alert"]["status"] == (
            "applied"
        )
        get_review_store().connection.close()
        get_review_store.cache_clear()
        print("End-to-end demo smoke test passed (8/8 evaluation cases)")


if __name__ == "__main__":
    main()
