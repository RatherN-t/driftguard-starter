import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    AlertProvenance,
    AnalysisRunRequest,
    AnalysisRunResult,
    ClaimCandidate,
    DecisionExtractionResult,
    DriftAlert,
    DriftAssessment,
    EvidenceSpan,
    SourceLinkSummary,
    TranscriptIngestionResult,
)
from apps.api.app.integrations.github_client import (
    GitHubClient,
    ParsedPR,
    parse_pr_url,
    parse_repository_url,
)
from apps.api.app.integrations.google_docs_client import (
    GoogleDocsClient,
    parse_google_doc_url,
)
from apps.api.app.services.alignment_outputs import AlignmentOutputService
from apps.api.app.services.claim_extraction import ClaimExtractionService
from apps.api.app.services.document_changes import build_document_change
from apps.api.app.services.document_chunking import chunk_demo_architecture
from apps.api.app.services.drift import DriftClassificationService, match_claim_candidates
from apps.api.app.services.github_evidence import normalize_pull_request_evidence
from apps.api.app.services.google_docs_evidence import normalize_google_document
from apps.api.app.services.transcripts import (
    DecisionExtractionService,
    TranscriptionUnavailable,
    parse_text_transcript,
    transcript_evidence,
)

ROOT = Path(__file__).resolve().parents[4]
DEMO_DOCUMENT_URLS = {"demo://architecture_doc.md", "demo/architecture_doc.md"}
DEMO_DOCUMENT_URI = "demo://architecture_doc.md"
DEMO_REPOSITORY_URL = "https://github.com/example/driftguard-demo"
DEMO_PR_URL = f"{DEMO_REPOSITORY_URL}/pull/7"
DEMO_OBSERVED_AT = datetime(2026, 7, 31, tzinfo=UTC)


class AnalysisUnavailable(RuntimeError):
    pass


def run_analysis(
    request: AnalysisRunRequest,
    settings: Settings,
    *,
    github_client: object | None = None,
    google_client: object | None = None,
) -> AnalysisRunResult:
    repository = parse_repository_url(request.repository_url)
    parsed_pr = parse_pr_url(request.pull_request_url)
    if (repository.owner, repository.repo) != (parsed_pr.owner, parsed_pr.repo):
        raise ValueError("GitHub repository and pull request must refer to the same repository")

    observed_at = datetime.now(UTC)
    document_evidence, document_mode = _load_document(
        request.document_url,
        settings,
        observed_at=observed_at,
        google_client=google_client,
    )
    implementation_evidence, metadata, files, pr_mode = _load_pull_request(
        parsed_pr,
        settings,
        observed_at=observed_at,
        github_client=github_client,
    )
    fixture_mode = document_mode == "demo_fixture" and pr_mode == "demo_fixture"
    inference_settings = _inference_settings(settings, fixture_mode=fixture_mode)

    extraction = ClaimExtractionService(inference_settings)
    document_claims = extraction.extract_document_claims(document_evidence)
    code_claims = extraction.extract_code_claims(implementation_evidence)
    all_evidence = document_evidence + implementation_evidence
    candidates = match_claim_candidates(
        document_claims.claims,
        code_claims.implementation_claims,
        all_evidence,
    )
    if not candidates:
        raise AnalysisUnavailable("The linked sources produced no comparable claims")
    selection = _select_actionable_candidate(
        candidates,
        DriftClassificationService(inference_settings),
        all_evidence,
    )
    if selection is None:
        raise AnalysisUnavailable(
            "The strongest linked claims did not produce an actionable document update"
        )
    candidate, assessment = selection
    outputs = AlignmentOutputService(inference_settings)
    explanations = outputs.generate_explanations(candidate, assessment, all_evidence)
    proposal = outputs.propose_patch(candidate, assessment, all_evidence)
    alert = DriftAlert(
        id=_alert_id(assessment.evidence_ids),
        status="pending_review",
        title=str(metadata.get("title") or "Linked source behavior changed"),
        existing_claim=candidate.document_claim,
        implementation_claim=candidate.implementation_claim,
        document_evidence=_selected_evidence(
            document_evidence, candidate.document_claim.evidence_ids
        ),
        implementation_evidence=_selected_evidence(
            implementation_evidence, candidate.implementation_claim.evidence_ids
        ),
        classification=assessment,
        confidence=assessment.confidence,
        uncertainty=assessment.missing_evidence + proposal.unresolved_items,
        explanations=explanations,
        proposed_canonical_statement=assessment.proposed_canonical_statement,
        patch=proposal,
        provenance=AlertProvenance(
            mode="demo_fixture" if fixture_mode else "live",
            is_demo=fixture_mode,
            label=(
                "DEMO DATA - linked local document and PR fixtures"
                if fixture_mode
                else "Live Google Docs and GitHub evidence"
            ),
            inference_mode="demo_fixture_rules" if fixture_mode else "mistral",
            document_source_id=document_evidence[0].source_id,
            implementation_source_id=parsed_pr.source_id,
        ),
        created_at=observed_at,
    )
    transcript_settings = (
        settings
        if request.transcript_text and settings.mistral_api_key
        else inference_settings
    )
    transcript = _load_transcript(
        request, transcript_settings, observed_at=observed_at
    )
    sources = _source_summaries(
        request,
        parsed_pr,
        alert,
        document_mode=document_mode,
        pr_mode=pr_mode,
        metadata=metadata,
        files=files,
        transcript=transcript,
    )
    return AnalysisRunResult(
        alert=alert,
        sources=sources,
        transcript=transcript,
        document_change=build_document_change(alert),
    )


def build_default_analysis(settings: Settings) -> AnalysisRunResult:
    return run_analysis(
        AnalysisRunRequest(
            document_url=DEMO_DOCUMENT_URI,
            repository_url=DEMO_REPOSITORY_URL,
            pull_request_url=DEMO_PR_URL,
            use_demo_transcript=True,
        ),
        settings,
    )


def _select_actionable_candidate(
    candidates: list[ClaimCandidate],
    classifier: object,
    evidence: list[EvidenceSpan],
) -> tuple[ClaimCandidate, DriftAssessment] | None:
    for candidate in candidates:
        assessment = classifier.classify(candidate, evidence)
        if assessment.is_actionable and assessment.proposed_canonical_statement:
            return candidate, assessment
    return None


def _load_document(
    url: str,
    settings: Settings,
    *,
    observed_at: datetime,
    google_client: object | None,
) -> tuple[list[EvidenceSpan], str]:
    if url in DEMO_DOCUMENT_URLS:
        content = (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8")
        return chunk_demo_architecture(content, observed_at=DEMO_OBSERVED_AT), "demo_fixture"
    document_id = parse_google_doc_url(url)
    if google_client is None:
        if not Path(settings.google_service_account_file).is_file():
            raise AnalysisUnavailable(
                "Google Docs linking requires GOOGLE_SERVICE_ACCOUNT_FILE"
            )
        google_client = GoogleDocsClient(settings.google_service_account_file)
    document = google_client.get_document(document_id)
    return (
        normalize_google_document(document, observed_at=observed_at, source_uri=url),
        "live",
    )


def _load_pull_request(
    parsed: ParsedPR,
    settings: Settings,
    *,
    observed_at: datetime,
    github_client: object | None,
) -> tuple[list[EvidenceSpan], dict, list[dict], str]:
    if parsed.canonical_url == DEMO_PR_URL:
        metadata = json.loads(
            (ROOT / "demo" / "pr_metadata.json").read_text(encoding="utf-8")
        )
        files = [
            {"filename": filename, "status": "modified"}
            for filename in metadata["files"]
        ]
        full_files = {
            filename: (ROOT / "demo" / "code_after" / filename).read_text(
                encoding="utf-8"
            )
            for filename in metadata["files"]
        }
        return (
            normalize_pull_request_evidence(
                parsed,
                metadata=metadata,
                files=files,
                full_files=full_files,
                observed_at=DEMO_OBSERVED_AT,
            ),
            metadata,
            files,
            "demo_fixture",
        )

    if github_client is not None:
        result = github_client.fetch_pr(parsed, include_full_files=True)
    else:
        token = settings.github_token
        with GitHubClient(
            token.get_secret_value() if token else None,
            max_changed_files=settings.github_max_changed_files,
            max_file_bytes=settings.github_max_file_bytes,
        ) as client:
            result = client.fetch_pr(parsed, include_full_files=True)
    files = result["files"]
    return (
        normalize_pull_request_evidence(
            parsed,
            metadata=result["pr"],
            files=files,
            full_files=result["full_files"],
            observed_at=observed_at,
        ),
        result["pr"],
        files,
        "live",
    )


def _load_transcript(
    request: AnalysisRunRequest,
    settings: Settings,
    *,
    observed_at: datetime,
) -> TranscriptIngestionResult | None:
    text = request.transcript_text
    is_demo = request.use_demo_transcript
    if is_demo:
        text = (ROOT / "demo" / "meeting_transcript.txt").read_text(encoding="utf-8")
    if not text or not text.strip():
        return None
    transcript = parse_text_transcript(text)
    evidence = transcript_evidence(
        transcript,
        source_id=(
            "transcript:demo/meeting_transcript.txt"
            if is_demo
            else "transcript:linked-text"
        ),
        observed_at=DEMO_OBSERVED_AT if is_demo else observed_at,
    )
    try:
        decisions = DecisionExtractionService(settings).extract(evidence)
        label = (
            "DEMO DATA - local timestamped meeting transcript"
            if is_demo
            else "Linked timestamped meeting transcript"
        )
    except TranscriptionUnavailable:
        decisions = DecisionExtractionResult(decisions=[])
        label = "Linked transcript stored; configure MISTRAL_API_KEY to extract decisions"
    return TranscriptIngestionResult(
        provenance={
            "mode": "demo_fixture" if is_demo else "linked_text",
            "is_demo": is_demo,
            "label": label,
        },
        transcript=transcript,
        evidence=evidence,
        decisions=decisions,
    )


def _inference_settings(settings: Settings, *, fixture_mode: bool) -> Settings:
    if fixture_mode:
        return settings.model_copy(update={"demo_mode": True, "mistral_api_key": None})
    if not settings.mistral_api_key:
        raise AnalysisUnavailable("Live source analysis requires MISTRAL_API_KEY")
    return settings.model_copy(update={"demo_mode": False})


def _source_summaries(
    request: AnalysisRunRequest,
    parsed_pr: ParsedPR,
    alert: DriftAlert,
    *,
    document_mode: str,
    pr_mode: str,
    metadata: dict,
    files: list[dict],
    transcript: TranscriptIngestionResult | None,
) -> list[SourceLinkSummary]:
    document = alert.document_evidence[0]
    sources = [
        SourceLinkSummary(
            role="document",
            mode=document_mode,
            label=document.heading_path[0] or "Architecture document",
            uri=request.document_url,
            source_id=document.source_id,
            source_version=document.source_version,
            details=[f"Patch target: {alert.patch.target_artifact_id}"],
        ),
        SourceLinkSummary(
            role="repository",
            mode=pr_mode,
            label=f"{parsed_pr.owner}/{parsed_pr.repo}",
            uri=parsed_pr.repository_url,
            source_id=f"github:{parsed_pr.owner}/{parsed_pr.repo}",
            source_version=alert.implementation_evidence[0].source_version,
            details=["Read-only repository context"],
        ),
        SourceLinkSummary(
            role="pull_request",
            mode=pr_mode,
            label=f"PR #{parsed_pr.number}: {metadata.get('title') or 'Untitled'}",
            uri=parsed_pr.canonical_url,
            source_id=parsed_pr.source_id,
            source_version=alert.implementation_evidence[0].source_version,
            details=[
                f"Changed file: {item['filename']}"
                for item in files
                if isinstance(item.get("filename"), str)
            ],
        ),
    ]
    if transcript is not None:
        first = transcript.evidence[0]
        sources.append(
            SourceLinkSummary(
                role="transcript",
                mode="demo_fixture" if transcript.provenance["is_demo"] else "live",
                label=str(transcript.provenance["label"]),
                uri="demo://meeting_transcript.txt" if request.use_demo_transcript else "upload://transcript-text",
                source_id=first.source_id,
                source_version=first.source_version,
                details=[f"{len(transcript.transcript.segments)} timestamped segments"],
            )
        )
    return sources


def _selected_evidence(
    evidence: list[EvidenceSpan], evidence_ids: list[str]
) -> list[EvidenceSpan]:
    selected = [item for item in evidence if item.id in evidence_ids]
    if not selected:
        raise AnalysisUnavailable("Selected claim has no source evidence")
    return selected


def _alert_id(evidence_ids: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(evidence_ids)).encode("utf-8")).hexdigest()
    return f"alert:{digest[:24]}"
