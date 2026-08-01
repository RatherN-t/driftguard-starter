from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import DriftAlert, WriteResult
from apps.api.app.integrations.google_docs_client import GoogleDocsClient
from apps.api.app.services.document_chunking import DEMO_ARCHITECTURE_SOURCE_VERSION
from apps.api.app.services.review_store import InvalidReviewTransition, ReviewStore

ROOT = Path(__file__).resolve().parents[4]
DEMO_OUTPUT = ROOT / "uploads" / "demo_architecture_doc.approved.md"
DEMO_TEMP_OUTPUT = ROOT / "uploads" / "demo_architecture_doc.approved.tmp"


class WriteBackUnavailable(RuntimeError):
    pass


class WriteBackService:
    def __init__(
        self,
        settings: Settings,
        store: ReviewStore,
        *,
        google_client: GoogleDocsClient | None = None,
    ):
        self.settings = settings
        self.store = store
        self.google_client = google_client

    def apply(self, alert: DriftAlert, *, actor_id: str) -> WriteResult:
        if self.store.current_status(alert) != "approved":
            raise InvalidReviewTransition("Patch application requires approved state")
        if self.settings.demo_mode:
            target, revision = _apply_demo_copy(alert)
            event = self.store.mark_applied(alert, actor_id=actor_id)
            return WriteResult(
                status="applied",
                mode="demo_local_copy",
                target=target,
                revision=revision,
                audit_event=event,
            )
        if alert.provenance.is_demo:
            raise WriteBackUnavailable("Demo evidence cannot be written to a live document")
        if not self.settings.google_write_enabled:
            raise WriteBackUnavailable("Google write-back is disabled")
        client = self.google_client or GoogleDocsClient(self.settings.google_service_account_file)
        client.apply_patch(alert.patch.target_artifact_id, alert.patch)
        event = self.store.mark_applied(alert, actor_id=actor_id)
        return WriteResult(
            status="applied",
            mode="google_docs",
            target=alert.patch.target_artifact_id,
            revision=alert.patch.expected_revision,
            audit_event=event,
        )


def reset_demo_copy() -> None:
    for path in (DEMO_OUTPUT, DEMO_TEMP_OUTPUT):
        if path.is_file():
            path.unlink()


def _apply_demo_copy(alert: DriftAlert) -> tuple[str, str]:
    if alert.patch.expected_revision != DEMO_ARCHITECTURE_SOURCE_VERSION:
        raise WriteBackUnavailable("Demo document revision changed before apply")
    source = ROOT / "demo" / "architecture_doc.md"
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    for operation in alert.patch.operations:
        if operation.operation != "replace_range" or not operation.original_text:
            raise WriteBackUnavailable("Demo MVP supports replace_range operations only")
        start, end = _line_range(operation.locator)
        if start != end:
            raise WriteBackUnavailable("Demo MVP patch must target one complete line")
        existing = lines[start - 1].rstrip("\r\n")
        if existing != operation.original_text:
            raise WriteBackUnavailable("Demo document target text changed before apply")
        newline = "\n" if lines[start - 1].endswith(("\n", "\r")) else ""
        lines[start - 1] = operation.replacement_text + newline
    DEMO_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEMO_TEMP_OUTPUT.write_text("".join(lines), encoding="utf-8")
    DEMO_TEMP_OUTPUT.replace(DEMO_OUTPUT)
    return str(DEMO_OUTPUT.relative_to(ROOT)), alert.patch.expected_revision


def _line_range(locator: str) -> tuple[int, int]:
    if not locator.startswith("lines:") or "-" not in locator:
        raise WriteBackUnavailable("Demo patch locator must use lines:start-end")
    start_text, end_text = locator.removeprefix("lines:").split("-", 1)
    start, end = int(start_text), int(end_text)
    if start < 1 or end < start:
        raise WriteBackUnavailable("Demo patch line range is invalid")
    return start, end
