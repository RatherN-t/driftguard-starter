from fastapi import APIRouter, HTTPException, status

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import AnalysisRunRequest, AnalysisRunResult
from apps.api.app.integrations.github_client import GitHubClientError
from apps.api.app.services.active_analysis import get_active_analysis_store
from apps.api.app.services.analysis_pipeline import (
    AnalysisUnavailable,
    build_default_analysis,
    run_analysis,
)
from apps.api.app.services.auto_approval import auto_approve_and_apply
from apps.api.app.services.document_changes import build_document_change
from apps.api.app.services.review_store import get_review_store

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/current", response_model=AnalysisRunResult)
def current_analysis() -> AnalysisRunResult:
    result = get_active_analysis_store().get() or build_default_analysis(get_settings())
    settings = get_settings()
    review_status = auto_approve_and_apply(
        result.alert, settings=settings, store=get_review_store()
    )
    alert = result.alert.model_copy(update={"status": review_status})
    return result.model_copy(
        update={"alert": alert, "document_change": build_document_change(alert)}
    )


@router.post("/run", response_model=AnalysisRunResult)
def analyze_linked_sources(request: AnalysisRunRequest) -> AnalysisRunResult:
    try:
        settings = get_settings()
        result = run_analysis(request, settings)
        review_status = auto_approve_and_apply(
            result.alert, settings=settings, store=get_review_store()
        )
        result = result.model_copy(
            update={"alert": result.alert.model_copy(update={"status": review_status})}
        )
        get_active_analysis_store().set(result)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except AnalysisUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except GitHubClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
