import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_URL = os.environ.get("DRIFTGUARD_API_URL", "http://127.0.0.1:8000").rstrip("/")
WEB_URL = os.environ.get("DRIFTGUARD_WEB_URL", "http://127.0.0.1:3000").rstrip("/")

DEMO_REQUEST = {
    "document_url": "demo://architecture_doc.md",
    "repository_url": "https://github.com/example/driftguard-demo",
    "pull_request_url": "https://github.com/example/driftguard-demo/pull/7",
    "transcript_text": None,
    "use_demo_transcript": True,
}


def main() -> None:
    with httpx.Client(timeout=30) as client:
        _ok(client.get(f"{API_URL}/health"), "backend health")
        _ok(client.post(f"{API_URL}/api/demo/reset"), "demo reset")

        analysis_response = client.post(
            f"{API_URL}/api/analysis/run", json=DEMO_REQUEST
        )
        _ok(analysis_response, "linked demo analysis")
        analysis = analysis_response.json()
        alert = analysis["alert"]
        sources = {item["role"]: item for item in analysis["sources"]}
        assert set(sources) == {"document", "repository", "pull_request", "transcript"}
        assert sources["document"]["uri"] == "demo://architecture_doc.md"
        assert sources["repository"]["uri"] == (
            "https://github.com/example/driftguard-demo"
        )
        assert sources["pull_request"]["uri"].endswith("/pull/7")
        assert analysis["transcript"]["decisions"]["decisions"][0]["status"] == (
            "confirmed"
        )
        assert "synchronously" in analysis["document_change"]["before_content"]
        assert "returns HTTP 202" in analysis["document_change"]["proposed_content"]

        # Human review is disabled: no approve/apply call is needed, the
        # patch is auto-approved and written to the demo copy immediately.
        assert alert["status"] == "applied"
        assert analysis["document_change"]["applied_content"] == (
            analysis["document_change"]["proposed_content"]
        )

        mismatch = client.post(
            f"{API_URL}/api/analysis/run",
            json={
                **DEMO_REQUEST,
                "repository_url": "https://github.com/example/not-the-pr-repository",
            },
        )
        assert mismatch.status_code == 422
        assert "same repository" in mismatch.json()["detail"]

        alert_id = alert["id"]
        already_applied = client.post(
            f"{API_URL}/api/alerts/{alert_id}/apply",
            json={"actor_id": "uat-reviewer"},
        )
        assert already_applied.status_code == 409
        output = ROOT / analysis["document_change"]["target"]
        assert output.is_file()
        after_apply = client.get(
            f"{API_URL}/api/alerts/{alert_id}/document-change"
        ).json()
        assert after_apply["applied_content"] == after_apply["proposed_content"]
        assert "returns HTTP 202" in output.read_text(encoding="utf-8")

        audit = client.get(f"{API_URL}/api/alerts/{alert_id}/audit").json()
        assert [item["event_type"] for item in audit] == [
            "alert_approved",
            "patch_applied",
        ]
        assert audit[0]["actor_id"] == "system:auto-approval"

        web = client.get(WEB_URL)
        _ok(web, "frontend")
        assert "Link the document people trust" in web.text
        assert "Build alignment view" in web.text

        _ok(client.post(f"{API_URL}/api/demo/reset"), "final reset")
        assert not output.exists()
        assert client.get(f"{API_URL}/api/analysis/current").json()["alert"][
            "status"
        ] == "applied"

    print(
        "UAT passed: source linking, validation, transcript, auto-approval, "
        "actual document write, audit, frontend, and reset"
    )


def _ok(response: httpx.Response, label: str) -> None:
    if not response.is_success:
        raise AssertionError(f"{label} failed with HTTP {response.status_code}")


if __name__ == "__main__":
    main()
