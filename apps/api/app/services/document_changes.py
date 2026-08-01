from datetime import UTC, datetime
from pathlib import Path

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import DocumentChangeView, DriftAlert
from apps.api.app.integrations.google_docs_client import GoogleDocsClient
from apps.api.app.services.google_docs_evidence import normalize_google_document
from apps.api.app.services.writeback import DEMO_OUTPUT

ROOT = Path(__file__).resolve().parents[4]
DEMO_DOCUMENT = ROOT / "demo" / "architecture_doc.md"


def build_document_change(
    alert: DriftAlert, *, google_client: GoogleDocsClient | None = None
) -> DocumentChangeView:
    document_span = alert.document_evidence[0]
    if alert.provenance.is_demo:
        before = DEMO_DOCUMENT.read_text(encoding="utf-8")
        proposed = _apply_text_operations(before, alert)
        applied = DEMO_OUTPUT.read_text(encoding="utf-8") if DEMO_OUTPUT.is_file() else None
        return DocumentChangeView(
            mode="demo_local_copy",
            document_label=document_span.heading_path[0] or "Demo architecture document",
            source_uri=document_span.source_uri or "demo://architecture_doc.md",
            target=str(DEMO_OUTPUT.relative_to(ROOT)),
            source_version=alert.patch.expected_revision,
            before_content=before,
            proposed_content=proposed,
            applied_content=applied,
            operations=alert.patch.operations,
        )

    before = document_span.content
    proposed = _apply_text_operations(before, alert)
    applied = None
    if alert.status == "applied":
        client = google_client or GoogleDocsClient(
            get_settings().google_service_account_file
        )
        document = client.get_document(alert.patch.target_artifact_id)
        spans = normalize_google_document(
            document,
            observed_at=datetime.now(UTC),
            source_uri=document_span.source_uri,
        )
        matching = next(
            (item for item in spans if item.heading_path == document_span.heading_path),
            None,
        )
        if matching is None:
            raise ValueError("Applied Google document section could not be verified")
        applied = matching.content
    return DocumentChangeView(
        mode="google_docs",
        document_label=document_span.heading_path[0] or document_span.source_id,
        source_uri=document_span.source_uri or "",
        target=alert.patch.target_artifact_id,
        source_version=alert.patch.expected_revision,
        before_content=before,
        proposed_content=proposed,
        applied_content=applied,
        operations=alert.patch.operations,
    )


def _apply_text_operations(content: str, alert: DriftAlert) -> str:
    updated = content
    for operation in alert.patch.operations:
        if not operation.original_text:
            continue
        if operation.original_text not in updated:
            raise ValueError("Proposed document target is not present in the source preview")
        updated = updated.replace(
            operation.original_text, operation.replacement_text, 1
        )
    return updated
