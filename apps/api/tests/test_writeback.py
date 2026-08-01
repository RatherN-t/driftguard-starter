from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import DocumentPatchProposal, PatchOperation
from apps.api.app.integrations.google_docs_client import (
    DocumentRevisionConflict,
    DocumentTargetConflict,
    GoogleDocsClient,
)
from apps.api.app.main import app
from apps.api.app.services.review_store import get_review_store
from apps.api.app.services.writeback import DEMO_OUTPUT


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'write.db'}")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    if DEMO_OUTPUT.is_file():
        DEMO_OUTPUT.unlink()
    test_client = TestClient(app)
    yield test_client
    if DEMO_OUTPUT.is_file():
        DEMO_OUTPUT.unlink()
    get_review_store().connection.close()
    get_review_store.cache_clear()
    get_settings.cache_clear()


def test_alert_is_auto_applied_to_the_demo_copy_with_no_manual_apply_call(
    client: TestClient,
) -> None:
    alert = client.get("/api/alerts").json()[0]
    duplicate_apply = client.post(
        f"/api/alerts/{alert['id']}/apply", json={"actor_id": "reviewer"}
    )

    assert alert["status"] == "applied"
    assert DEMO_OUTPUT.is_file()
    updated = DEMO_OUTPUT.read_text(encoding="utf-8")
    assert alert["proposed_canonical_statement"] in updated
    assert "calls the payment provider synchronously" not in updated
    assert duplicate_apply.status_code == 409
    assert client.get(f"/api/alerts/{alert['id']}").json()["status"] == "applied"
    assert len(client.get(f"/api/alerts/{alert['id']}/audit").json()) == 2


def test_demo_apply_cannot_repeat_and_reset_removes_copy(client: TestClient) -> None:
    client.get("/api/alerts")
    alert = client.get("/api/alerts").json()[0]

    duplicate = client.post(
        f"/api/alerts/{alert['id']}/apply", json={"actor_id": "reviewer"}
    )
    reset = client.post("/api/demo/reset")

    assert duplicate.status_code == 409
    assert reset.status_code == 200
    assert not DEMO_OUTPUT.exists()


def test_google_apply_checks_revision_and_target_before_batch_update() -> None:
    success_docs = FakeDocsService(_document("rev-1", "old text"))
    client = GoogleDocsClient(drive_service=object(), docs_service=success_docs)
    result = client.apply_patch("doc-1", _proposal("rev-1", "old text"))

    assert result == {"revisionId": "rev-2"}
    assert success_docs.batch_calls == 1
    assert success_docs.last_body["writeControl"] == {"requiredRevisionId": "rev-1"}
    assert success_docs.last_body["requests"][0]["deleteContentRange"]["range"] == {
        "startIndex": 1,
        "endIndex": 9,
    }

    revision_docs = FakeDocsService(_document("rev-2", "old text"))
    with pytest.raises(DocumentRevisionConflict):
        GoogleDocsClient(drive_service=object(), docs_service=revision_docs).apply_patch(
            "doc-1", _proposal("rev-1", "old text")
        )
    assert revision_docs.batch_calls == 0

    target_docs = FakeDocsService(_document("rev-1", "new text"))
    with pytest.raises(DocumentTargetConflict):
        GoogleDocsClient(drive_service=object(), docs_service=target_docs).apply_patch(
            "doc-1", _proposal("rev-1", "old text")
        )
    assert target_docs.batch_calls == 0


def test_google_apply_reads_target_from_tab_aware_document() -> None:
    document = _document("rev-1", "old text")
    document["tabs"] = [{"documentTab": {"body": document.pop("body")}}]
    docs = FakeDocsService(document)

    result = GoogleDocsClient(drive_service=object(), docs_service=docs).apply_patch(
        "doc-1", _proposal("rev-1", "old text")
    )

    assert result == {"revisionId": "rev-2"}
    assert docs.batch_calls == 1


class FakeDocsService:
    def __init__(self, document: dict):
        self.document = document
        self.batch_calls = 0
        self.last_body: dict = {}

    def documents(self):
        return self

    def get(self, **_: object):
        self.mode = "get"
        return self

    def batchUpdate(self, **kwargs: object):
        self.mode = "batch"
        self.last_body = kwargs["body"]
        return self

    def execute(self):
        if self.mode == "get":
            return self.document
        self.batch_calls += 1
        return {"revisionId": "rev-2"}


def _document(revision: str, text: str) -> dict:
    return {
        "revisionId": revision,
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 1,
                                "endIndex": 9,
                                "textRun": {"content": text},
                            }
                        ]
                    }
                }
            ]
        },
    }


def _proposal(revision: str, original: str) -> DocumentPatchProposal:
    return DocumentPatchProposal(
        target_artifact_id="doc-1",
        expected_revision=revision,
        operations=[
            PatchOperation(
                operation="replace_range",
                locator="chars:1-9",
                original_text=original,
                replacement_text="replacement",
                evidence_ids=["ev-1"],
            )
        ],
        rationale="Update stale text.",
        evidence_ids=["ev-1"],
        confidence=1,
    )
