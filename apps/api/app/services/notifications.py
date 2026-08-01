import hashlib
import re

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    DriftAlert,
    EmailPreview,
    NotificationResult,
)
from apps.api.app.integrations.email_client import EmailMessage, SMTPEmailClient
from apps.api.app.services.review_store import ReviewStore

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class NotificationUnavailable(RuntimeError):
    pass


class NotificationService:
    def __init__(
        self,
        settings: Settings,
        store: ReviewStore,
        *,
        email_client: object | None = None,
    ):
        self.settings = settings
        self.store = store
        self.email_client = email_client

    def preview(self, alert: DriftAlert) -> EmailPreview:
        return EmailPreview(
            subject=f"DriftGuard review: {alert.title}",
            text=(
                f"What changed\n{alert.explanations.pm.what_changed}\n\n"
                f"Why it matters\n{alert.explanations.pm.why_it_matters}\n\n"
                f"Proposed wording\n{alert.proposed_canonical_statement}\n\n"
                f"Review ID\n{alert.id}\n"
            ),
            audience=["product manager", "developer"],
            evidence_ids=alert.classification.evidence_ids,
        )

    def send(
        self, alert: DriftAlert, *, recipients: list[str], actor_id: str
    ) -> NotificationResult:
        if self.store.current_status(alert) not in {"approved", "applied"}:
            raise NotificationUnavailable("Email delivery requires approved review state")
        if self.settings.email_mode != "smtp":
            raise NotificationUnavailable("SMTP delivery is not enabled")
        if not all(_EMAIL.fullmatch(item) for item in recipients):
            raise ValueError("Every notification recipient must be a valid email address")
        client = self.email_client or self._smtp_client()
        preview = self.preview(alert)
        key = _deduplication_key(alert.id, recipients, preview.text)
        if not self.store.record_notification(alert.id, key, actor_id=actor_id):
            raise NotificationUnavailable("This notification was already sent")
        try:
            client.send(
                EmailMessage(to=recipients, subject=preview.subject, text=preview.text)
            )
        except Exception as exc:
            self.store.remove_notification(alert.id, key)
            raise NotificationUnavailable("SMTP delivery failed") from exc
        return NotificationResult(
            status="sent", recipients=recipients, deduplication_key=key
        )

    def _smtp_client(self) -> SMTPEmailClient:
        if not (
            self.settings.smtp_host
            and self.settings.smtp_username
            and self.settings.smtp_password
            and self.settings.smtp_from
        ):
            raise NotificationUnavailable("SMTP configuration is incomplete")
        return SMTPEmailClient(
            host=self.settings.smtp_host,
            port=self.settings.smtp_port,
            username=self.settings.smtp_username,
            password=self.settings.smtp_password.get_secret_value(),
            sender=self.settings.smtp_from,
        )


def _deduplication_key(alert_id: str, recipients: list[str], text: str) -> str:
    payload = "\n".join([alert_id, *sorted(recipients), text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
