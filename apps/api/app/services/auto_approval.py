from apps.api.app.config import Settings
from apps.api.app.domain.schemas import DriftAlert
from apps.api.app.services.review_store import ReviewStore
from apps.api.app.services.writeback import WriteBackService, WriteBackUnavailable

AUTO_APPROVAL_ACTOR = "system:auto-approval"
AUTO_APPROVAL_COMMENT = "Auto-approved: human review is disabled for this workspace."


def auto_approve_and_apply(alert: DriftAlert, *, settings: Settings, store: ReviewStore) -> str:
    """Advance a freshly seen alert straight through approval and write-back.

    ADR-002's human approval gate is superseded by ADR-004: every alert is
    approved and applied automatically, with the decision still recorded in
    the audit trail under a system actor. Live write-back can still fall
    short of "applied" (e.g. Google write-back disabled) in which case the
    alert stays "approved" until it can be applied, same as before.
    """
    status = store.ensure_alert(alert)
    if status == "pending_review":
        store.transition(
            alert,
            action="approve",
            actor_id=AUTO_APPROVAL_ACTOR,
            comment=AUTO_APPROVAL_COMMENT,
        )
        status = "approved"
    if status == "approved":
        try:
            WriteBackService(settings, store).apply(alert, actor_id=AUTO_APPROVAL_ACTOR)
            status = "applied"
        except WriteBackUnavailable:
            pass
    return status
