import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import AlertProvenance, DriftAlert
from apps.api.app.integrations.github_client import parse_pr_url
from apps.api.app.services.alignment_outputs import AlignmentOutputService
from apps.api.app.services.claim_extraction import ClaimExtractionService
from apps.api.app.services.document_chunking import chunk_demo_architecture
from apps.api.app.services.drift import DriftClassificationService, match_claim_candidates
from apps.api.app.services.github_evidence import normalize_pull_request_evidence

ROOT = Path(__file__).resolve().parents[4]
DEMO_OBSERVED_AT = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)


def build_demo_alert(settings: Settings) -> DriftAlert:
    fixture_settings = settings.model_copy(
        update={"demo_mode": True, "mistral_api_key": None}
    )
    document_evidence = chunk_demo_architecture(
        (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8"),
        observed_at=DEMO_OBSERVED_AT,
    )
    metadata = json.loads((ROOT / "demo" / "pr_metadata.json").read_text(encoding="utf-8"))
    parsed = parse_pr_url(metadata["url"])
    files = [{"filename": filename, "status": "modified"} for filename in metadata["files"]]
    full_files = {
        filename: (ROOT / "demo" / "code_after" / filename).read_text(encoding="utf-8")
        for filename in metadata["files"]
    }
    implementation_evidence = normalize_pull_request_evidence(
        parsed,
        metadata=metadata,
        files=files,
        full_files=full_files,
        observed_at=DEMO_OBSERVED_AT,
    )
    extraction = ClaimExtractionService(fixture_settings)
    document_claims = extraction.extract_document_claims(document_evidence)
    code_claims = extraction.extract_code_claims(implementation_evidence)
    all_evidence = document_evidence + implementation_evidence
    candidates = match_claim_candidates(
        document_claims.claims,
        code_claims.implementation_claims,
        all_evidence,
    )
    if not candidates:
        raise RuntimeError("Demo fixtures produced no claim candidate")
    candidate = candidates[0]
    assessment = DriftClassificationService(fixture_settings).classify(candidate, all_evidence)
    outputs = AlignmentOutputService(fixture_settings)
    explanations = outputs.generate_explanations(candidate, assessment, all_evidence)
    patch = outputs.propose_patch(candidate, assessment, all_evidence)
    alert_id = _alert_id(assessment.evidence_ids)
    return DriftAlert(
        id=alert_id,
        status="pending_review",
        title="Checkout processing model changed",
        existing_claim=candidate.document_claim,
        implementation_claim=candidate.implementation_claim,
        document_evidence=[
            item for item in document_evidence if item.id in candidate.document_claim.evidence_ids
        ],
        implementation_evidence=[
            item
            for item in implementation_evidence
            if item.id in candidate.implementation_claim.evidence_ids
        ],
        classification=assessment,
        confidence=assessment.confidence,
        uncertainty=assessment.missing_evidence + patch.unresolved_items,
        explanations=explanations,
        proposed_canonical_statement=assessment.proposed_canonical_statement or "",
        patch=patch,
        provenance=AlertProvenance(
            mode="demo_fixture",
            is_demo=True,
            label="DEMO DATA - local document and PR fixtures",
            inference_mode="demo_fixture_rules",
            document_source_id=document_evidence[0].source_id,
            implementation_source_id=parsed.source_id,
        ),
        created_at=DEMO_OBSERVED_AT,
    )


def _alert_id(evidence_ids: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(evidence_ids)).encode("utf-8")).hexdigest()
    return f"alert:{digest[:24]}"
