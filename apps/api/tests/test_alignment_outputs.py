from datetime import UTC, datetime

import pytest

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    AtomicClaim,
    ClaimCandidate,
    DocumentPatchProposal,
    DriftAssessment,
    EvidenceSpan,
    PatchOperation,
)
from apps.api.app.services.alignment_outputs import (
    AlignmentOutputService,
    AlignmentOutputUnavailable,
)

OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_demo_role_views_and_patch_are_grounded_in_same_evidence() -> None:
    candidate, assessment, evidence = _scenario()
    service = AlignmentOutputService(_settings())

    explanations = service.generate_explanations(candidate, assessment, evidence)
    patch = service.propose_patch(candidate, assessment, evidence)

    assert explanations.evidence_ids == ["doc", "api", "worker"]
    assert explanations.pm.what_changed
    assert explanations.developer.stale_claim == candidate.document_claim.statement
    assert patch.target_artifact_id == "demo/architecture_doc.md"
    assert patch.expected_revision == "fixture-v1"
    assert patch.operations[0].locator == "lines:5-5"
    assert patch.operations[0].original_text == evidence[0].content.split("\n")[-1]
    assert patch.operations[0].replacement_text == assessment.proposed_canonical_statement
    assert patch.evidence_ids == ["doc", "api", "worker"]


def test_nonactionable_assessment_does_not_propose_write_patch() -> None:
    candidate, assessment, evidence = _scenario()
    assessment = assessment.model_copy(
        update={"is_actionable": False, "proposed_canonical_statement": None}
    )

    with pytest.raises(AlignmentOutputUnavailable, match="No actionable"):
        AlignmentOutputService(_settings()).propose_patch(candidate, assessment, evidence)


def test_live_mode_without_mistral_fails_clearly() -> None:
    candidate, assessment, evidence = _scenario()
    settings = Settings(_env_file=None, demo_mode=False, mistral_api_key=None)

    with pytest.raises(AlignmentOutputUnavailable, match="Mistral is required"):
        AlignmentOutputService(settings).generate_explanations(candidate, assessment, evidence)


def test_live_patch_uses_exact_cited_google_paragraph_not_model_target_text() -> None:
    candidate, assessment, evidence = _scenario()
    original = "Checkout is synchronous and returns HTTP 200."
    evidence[0] = _evidence(
        "doc",
        "gdoc:doc-1",
        "google_doc",
        "live-rev-1",
        "chars:100-166",
        f"Payment processing\n{original}",
    )
    model_proposal = DocumentPatchProposal(
        target_artifact_id="invented-target",
        expected_revision="invented-revision",
        operations=[
            PatchOperation(
                operation="replace_range",
                locator="chars:1-2",
                original_text="paraphrased model target",
                replacement_text="unsupported model replacement",
                evidence_ids=["doc"],
            )
        ],
        rationale="Update the stale contract.",
        evidence_ids=["doc", "api", "worker"],
        confidence=0.9,
    )

    patch = AlignmentOutputService(
        Settings(_env_file=None, demo_mode=False, mistral_api_key=None),
        gateway=FakeGateway(model_proposal),
    ).propose_patch(candidate, assessment, evidence)

    operation = patch.operations[0]
    assert patch.target_artifact_id == "doc-1"
    assert patch.expected_revision == "live-rev-1"
    assert operation.locator == "chars:120-165"
    assert operation.original_text == original
    assert operation.replacement_text == assessment.proposed_canonical_statement


class FakeGateway:
    def __init__(self, result: object):
        self.result = result

    def parse_with_evidence(self, **_: object) -> object:
        return self.result


def _scenario() -> tuple[ClaimCandidate, DriftAssessment, list[EvidenceSpan]]:
    evidence = [
        _evidence(
            "doc",
            "demo/architecture_doc.md",
            "demo_fixture",
            "fixture-v1",
            "lines:3-5",
            "## Payment processing\n\nCheckout is synchronous and returns HTTP 200.",
        ),
        _evidence(
            "api",
            "github:example/repo:pull/7",
            "github_pr",
            "demoabc123",
            "file:payment_api.py:lines:1-20",
            "checkout returns HTTP 202 with pending state",
        ),
        _evidence(
            "worker",
            "github:example/repo:pull/7",
            "github_pr",
            "demoabc123",
            "file:payment_worker.py:lines:1-20",
            "run_payment_job charges provider",
        ),
    ]
    document = AtomicClaim(
        subject="checkout payment processing",
        statement="Checkout is synchronous and returns HTTP 200.",
        claim_type="current_state",
        status="observed",
        confidence=1,
        evidence_ids=["doc"],
    )
    implementation = AtomicClaim(
        subject="checkout payment processing",
        statement="Checkout returns HTTP 202 and a worker processes payment.",
        claim_type="implementation",
        status="observed",
        confidence=1,
        evidence_ids=["api", "worker"],
    )
    candidate = ClaimCandidate(
        document_claim=document,
        implementation_claim=implementation,
        score=0.7,
        shared_terms=["checkout", "payment"],
    )
    assessment = DriftAssessment(
        relationship="stale_documentation",
        is_actionable=True,
        severity="high",
        confidence=0.98,
        concise_reason="The documented synchronous response conflicts with HTTP 202 and worker evidence.",
        evidence_ids=["doc", "api", "worker"],
        proposed_canonical_statement=(
            "Checkout creates a pending payment, returns HTTP 202, and completes provider "
            "processing in PaymentJob."
        ),
    )
    return candidate, assessment, evidence


def _settings() -> Settings:
    return Settings(_env_file=None, demo_mode=True, mistral_api_key=None)


def _evidence(
    evidence_id: str,
    source_id: str,
    source_type: str,
    version: str,
    locator: str,
    content: str,
) -> EvidenceSpan:
    return EvidenceSpan(
        id=evidence_id,
        source_id=source_id,
        source_type=source_type,
        source_version=version,
        locator=locator,
        observed_at=OBSERVED_AT,
        content=content,
    )
