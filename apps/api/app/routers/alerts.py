from fastapi import APIRouter, HTTPException, status

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import (
    AuditEvent,
    DocumentChangeView,
    DriftAlert,
    EmailPreview,
    FeedbackRecord,
    FeedbackRequest,
    NotificationRequest,
    NotificationResult,
    ReviewDecisionRequest,
    WriteResult,
)
from apps.api.app.services.active_analysis import get_active_analysis_store
from apps.api.app.services.auto_approval import auto_approve_and_apply
from apps.api.app.services.demo_pipeline import build_demo_alert
from apps.api.app.services.document_changes import build_document_change
from apps.api.app.services.notifications import NotificationService, NotificationUnavailable
from apps.api.app.services.review_store import (
    InvalidReviewTransition,
    get_review_store,
)
from apps.api.app.services.writeback import WriteBackService, WriteBackUnavailable

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[DriftAlert])
def list_alerts() -> list[DriftAlert]:
    result = get_active_analysis_store().get()
    alert = result.alert if result is not None else build_demo_alert(get_settings())
    settings = get_settings()
    status = auto_approve_and_apply(alert, settings=settings, store=get_review_store())
    return [alert.model_copy(update={"status": status})]


@router.get("/{alert_id}", response_model=DriftAlert)
def get_alert(alert_id: str) -> DriftAlert:
    alert = _known_alert(alert_id)
    status = auto_approve_and_apply(alert, settings=get_settings(), store=get_review_store())
    return alert.model_copy(update={"status": status})


@router.post("/{alert_id}/approve", response_model=AuditEvent)
def approve_alert(alert_id: str, request: ReviewDecisionRequest) -> AuditEvent:
    return _transition(alert_id, request, action="approve")


@router.post("/{alert_id}/reject", response_model=AuditEvent)
def reject_alert(alert_id: str, request: ReviewDecisionRequest) -> AuditEvent:
    return _transition(alert_id, request, action="reject")


@router.get("/{alert_id}/audit", response_model=list[AuditEvent])
def alert_audit(alert_id: str) -> list[AuditEvent]:
    _known_alert(alert_id)
    return get_review_store().list_audit(alert_id)


@router.get("/{alert_id}/document-change", response_model=DocumentChangeView)
def alert_document_change(alert_id: str) -> DocumentChangeView:
    return build_document_change(_known_alert(alert_id))


@router.get("/{alert_id}/feedback", response_model=list[FeedbackRecord])
def alert_feedback(alert_id: str) -> list[FeedbackRecord]:
    _known_alert(alert_id)
    return get_review_store().list_feedback(alert_id)


@router.post("/{alert_id}/feedback", response_model=FeedbackRecord)
def record_alert_feedback(
    alert_id: str, request: FeedbackRequest
) -> FeedbackRecord:
    return get_review_store().record_feedback(
        _known_alert(alert_id),
        actor_id=request.actor_id,
        verdict=request.verdict,
        comment=request.comment,
    )


@router.post("/{alert_id}/apply", response_model=WriteResult)
def apply_alert(alert_id: str, request: ReviewDecisionRequest) -> WriteResult:
    alert = _known_alert(alert_id)
    try:
        return WriteBackService(get_settings(), get_review_store()).apply(
            alert, actor_id=request.actor_id
        )
    except InvalidReviewTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WriteBackUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{alert_id}/email/preview", response_model=EmailPreview)
def preview_alert_email(alert_id: str) -> EmailPreview:
    alert = _known_alert(alert_id)
    return NotificationService(get_settings(), get_review_store()).preview(alert)


@router.post("/{alert_id}/email/send", response_model=NotificationResult)
def send_alert_email(
    alert_id: str, request: NotificationRequest
) -> NotificationResult:
    alert = _known_alert(alert_id)
    try:
        return NotificationService(get_settings(), get_review_store()).send(
            alert, recipients=request.recipients, actor_id=request.actor_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotificationUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _transition(
    alert_id: str, request: ReviewDecisionRequest, *, action: str
) -> AuditEvent:
    alert = _known_alert(alert_id)
    try:
        return get_review_store().transition(
            alert,
            action=action,
            actor_id=request.actor_id,
            comment=request.comment,
            reason_code=request.reason_code,
        )
    except InvalidReviewTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _known_alert(alert_id: str) -> DriftAlert:
    result = get_active_analysis_store().get()
    alert = result.alert if result is not None else build_demo_alert(get_settings())
    if alert.id != alert_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert
