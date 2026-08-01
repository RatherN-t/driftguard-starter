from apps.api.app.config import Settings
from apps.api.app.domain.schemas import AlertProvenance, PatchOperation
from apps.api.app.services.demo_pipeline import build_demo_alert
from apps.api.app.services.document_changes import build_document_change


def test_applied_live_change_reads_actual_google_section() -> None:
    old = "Checkout calls the provider synchronously and returns HTTP 200."
    new = "Checkout persists a pending payment and returns HTTP 202."
    alert = build_demo_alert(
        Settings(_env_file=None, demo_mode=True, mistral_api_key=None)
    )
    document = alert.document_evidence[0].model_copy(
        update={
            "source_id": "gdoc:doc-1",
            "source_type": "google_doc",
            "source_uri": "https://docs.google.com/document/d/doc-1/edit",
            "source_version": "rev-1",
            "locator": "chars:20-82",
            "heading_path": ["Payment processing"],
            "content": f"Payment processing\n{old}",
        }
    )
    operation = PatchOperation(
        operation="replace_range",
        locator="chars:20-81",
        original_text=old,
        replacement_text=new,
        evidence_ids=alert.classification.evidence_ids,
    )
    live_alert = alert.model_copy(
        update={
            "status": "applied",
            "document_evidence": [document],
            "patch": alert.patch.model_copy(
                update={
                    "target_artifact_id": "doc-1",
                    "expected_revision": "rev-1",
                    "operations": [operation],
                }
            ),
            "provenance": AlertProvenance(
                mode="live",
                is_demo=False,
                label="Live Google Docs and GitHub evidence",
                inference_mode="mistral",
                document_source_id="gdoc:doc-1",
                implementation_source_id="github:owner/repo:pull/1",
            ),
        }
    )

    change = build_document_change(live_alert, google_client=FakeGoogleClient(new))

    assert change.applied_content == f"Payment processing\n{new}"
    assert change.proposed_content == change.applied_content


class FakeGoogleClient:
    def __init__(self, content: str):
        self.content = content

    def get_document(self, _: str) -> dict:
        heading = "Payment processing\n"
        body = self.content + "\n"
        return {
            "documentId": "doc-1",
            "revisionId": "rev-2",
            "body": {
                "content": [
                    _paragraph(1, 1 + len(heading), heading, "TITLE"),
                    _paragraph(
                        1 + len(heading),
                        1 + len(heading) + len(body),
                        body,
                        "NORMAL_TEXT",
                    ),
                ]
            },
        }


def _paragraph(start: int, end: int, text: str, style: str) -> dict:
    return {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [
                {"startIndex": start, "endIndex": end, "textRun": {"content": text}}
            ],
        },
    }
