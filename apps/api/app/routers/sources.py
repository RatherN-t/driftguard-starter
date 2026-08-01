import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import (
    GitHubPRRequest,
    GoogleSyncRequest,
    TranscriptIngestionResult,
    TranscriptTextRequest,
)
from apps.api.app.integrations.github_client import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubClientError,
    GitHubLimitError,
    GitHubTimeoutError,
    parse_pr_url,
)
from apps.api.app.integrations.google_docs_client import GoogleDocsClient
from apps.api.app.services.document_chunking import chunk_demo_architecture
from apps.api.app.services.github_evidence import normalize_pull_request_evidence
from apps.api.app.services.google_docs_evidence import normalize_google_document
from apps.api.app.services.transcripts import (
    DecisionExtractionService,
    TranscriptionUnavailable,
    VoxtralTranscriptionService,
    parse_text_transcript,
    transcript_evidence,
)

router = APIRouter(prefix="/api/sources", tags=["sources"])
ROOT = Path(__file__).resolve().parents[4]


@router.get("/transcript/demo", response_model=TranscriptIngestionResult)
def load_demo_transcript() -> TranscriptIngestionResult:
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo transcript is unavailable outside demo mode",
        )
    transcript = parse_text_transcript(
        (ROOT / "demo" / "meeting_transcript.txt").read_text(encoding="utf-8")
    )
    evidence = transcript_evidence(
        transcript,
        source_id="transcript:demo/meeting_transcript.txt",
        observed_at=datetime.now(UTC),
    )
    decisions = DecisionExtractionService(settings).extract(evidence)
    return TranscriptIngestionResult(
        provenance={
            "mode": "demo_fixture",
            "is_demo": True,
            "label": "DEMO DATA - local timestamped meeting transcript",
        },
        transcript=transcript,
        evidence=evidence,
        decisions=decisions,
    )


@router.post("/transcript/text", response_model=TranscriptIngestionResult)
def ingest_text_transcript(request: TranscriptTextRequest) -> TranscriptIngestionResult:
    settings = get_settings()
    transcript = parse_text_transcript(request.text)
    evidence = transcript_evidence(
        transcript,
        source_id="transcript:text-upload",
        observed_at=datetime.now(UTC),
    )
    decisions = DecisionExtractionService(settings).extract(evidence)
    return TranscriptIngestionResult(
        provenance={
            "mode": "demo_fixture" if settings.demo_mode else "live_text",
            "is_demo": settings.demo_mode,
            "label": "Timestamped text transcript",
        },
        transcript=transcript,
        evidence=evidence,
        decisions=decisions,
    )


@router.post("/transcript/audio", response_model=TranscriptIngestionResult)
async def ingest_audio_transcript(
    file: Annotated[UploadFile, File()],
) -> TranscriptIngestionResult:
    settings = get_settings()
    content = await file.read(settings.audio_max_bytes + 1)
    try:
        transcript = VoxtralTranscriptionService(settings).transcribe(
            filename=file.filename or "meeting-audio",
            content=content,
        )
        evidence = transcript_evidence(
            transcript,
            source_id=f"transcript:audio:{file.filename or 'meeting-audio'}",
            observed_at=datetime.now(UTC),
        )
        decisions = DecisionExtractionService(settings).extract(evidence)
        return TranscriptIngestionResult(
            provenance={"mode": "live_audio", "is_demo": False, "label": "Mistral Voxtral"},
            transcript=transcript,
            evidence=evidence,
            decisions=decisions,
        )
    except (TranscriptionUnavailable, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/google/sync")
def sync_google_documents(request: GoogleSyncRequest) -> dict:
    settings = get_settings()
    if settings.demo_mode:
        evidence = chunk_demo_architecture(
            (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8"),
            observed_at=datetime.now(UTC),
        )
        return {
            "provenance": {
                "mode": "demo_fixture",
                "is_demo": True,
                "label": "DEMO DATA - local architecture fixture, not Google Drive",
            },
            "documents": [{"id": "demo/architecture_doc.md", "name": "Architecture"}],
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
    folder_id = request.folder_id or settings.google_drive_folder_id
    if not folder_id or not Path(settings.google_service_account_file).is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Drive read credentials and folder ID are required",
        )
    try:
        client = GoogleDocsClient(settings.google_service_account_file)
        documents = client.list_folder_docs(folder_id)
        evidence = []
        for metadata in documents:
            document = client.get_document(metadata["id"])
            evidence.extend(
                normalize_google_document(
                    document,
                    observed_at=datetime.now(UTC),
                    source_uri=metadata.get("webViewLink"),
                )
            )
        return {
            "provenance": {"mode": "live_read", "is_demo": False, "label": "Google Drive"},
            "documents": documents,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Drive read failed",
        ) from exc


@router.post("/github/pr")
def ingest_github_pr(request: GitHubPRRequest) -> dict:
    settings = get_settings()
    try:
        parsed = parse_pr_url(str(request.url))
        demo_fixture = _load_matching_demo_pr(parsed.canonical_url) if settings.demo_mode else None
        if demo_fixture is not None:
            return demo_fixture
        token = settings.github_token
        with GitHubClient(
            token.get_secret_value() if token else None,
            max_changed_files=settings.github_max_changed_files,
            max_file_bytes=settings.github_max_file_bytes,
        ) as client:
            result = client.fetch_pr(parsed, include_full_files=True)
        evidence = normalize_pull_request_evidence(
            parsed,
            metadata=result["pr"],
            files=result["files"],
            full_files=result["full_files"],
            observed_at=datetime.now(UTC),
        )
        return {
            "provenance": {"mode": "live_read", "is_demo": False, "label": "GitHub API"},
            **result,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except GitHubLimitError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GitHubTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except GitHubClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _load_matching_demo_pr(canonical_url: str) -> dict | None:
    payload = json.loads((ROOT / "demo" / "pr_metadata.json").read_text(encoding="utf-8"))
    if payload["url"] != canonical_url:
        return None
    parsed = parse_pr_url(canonical_url)
    files = [{"filename": filename, "status": "modified"} for filename in payload["files"]]
    full_files = {
        filename: (ROOT / "demo" / "code_after" / filename).read_text(encoding="utf-8")
        for filename in payload["files"]
    }
    evidence = normalize_pull_request_evidence(
        parsed,
        metadata=payload,
        files=files,
        full_files=full_files,
        observed_at=datetime.now(UTC),
    )
    return {
        "provenance": {
            "mode": "demo_fixture",
            "is_demo": True,
            "label": "DEMO DATA - local GitHub PR fixture, not a live connector result",
        },
        "pr": payload,
        "files": files,
        "full_files": full_files,
        "evidence": [item.model_dump(mode="json") for item in evidence],
    }
