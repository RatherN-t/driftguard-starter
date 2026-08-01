from datetime import UTC, datetime

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import AtomicClaim, DriftAssessment, EvidenceSpan
from apps.api.app.services.analysis_pipeline import _select_actionable_candidate
from apps.api.app.services.drift import (
    DriftClassificationService,
    match_claim_candidates,
)

OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_candidate_matching_prefers_shared_subject_context_and_symbols() -> None:
    evidence = [
        _evidence("doc-payment", "google_doc", "Payment processing", "lines:3-5"),
        _evidence("doc-duplicate", "google_doc", "Duplicate requests", "lines:7-9"),
        _evidence("code-payment", "github_pr", "payment_api.py", "file:payment_api.py:lines:1-20"),
    ]
    documents = [
        _claim(
            "checkout payment processing",
            "Checkout calls the payment provider synchronously.",
            "doc-payment",
        ),
        _claim(
            "duplicate checkout requests",
            "Clients should avoid duplicate requests.",
            "doc-duplicate",
        ),
    ]
    implementation = _claim(
        "checkout payment processing",
        "The checkout handler queues PaymentJob and returns HTTP 202.",
        "code-payment",
        claim_type="implementation",
    )

    candidates = match_claim_candidates(documents, [implementation], evidence)

    assert candidates[0].document_claim == documents[0]
    assert candidates[0].score > candidates[1].score
    assert "checkout" in candidates[0].shared_terms
    assert "payment" in candidates[0].shared_terms


def test_demo_classification_detects_stale_documentation_with_citations() -> None:
    evidence = [
        _evidence("doc", "demo_fixture", "Payment processing", "lines:3-5"),
        _evidence("code", "github_pr", "payment_api.py", "file:payment_api.py:lines:1-20"),
    ]
    document = _claim(
        "checkout payment processing",
        "Checkout is synchronous and returns HTTP 200 after provider confirmation.",
        "doc",
    )
    implementation = _claim(
        "checkout payment processing",
        "Checkout returns HTTP 202 with pending state and a worker charges the provider.",
        "code",
        claim_type="implementation",
    )
    candidate = match_claim_candidates([document], [implementation], evidence)[0]

    result = DriftClassificationService(_settings()).classify(candidate, evidence)

    assert result.relationship == "stale_documentation"
    assert result.is_actionable is True
    assert result.severity == "high"
    assert result.evidence_ids == ["doc", "code"]
    assert result.proposed_canonical_statement


def test_future_state_and_disabled_flag_are_not_false_positive_drift() -> None:
    evidence = [
        _evidence("doc", "demo_fixture", "Roadmap", "lines:1-2"),
        _evidence("code", "github_pr", "flag.py", "file:flag.py:lines:1-2"),
    ]
    future = _claim(
        "checkout",
        "Checkout will become asynchronous in Q4.",
        "doc",
        claim_type="future_state",
    )
    current = _claim(
        "checkout",
        "Checkout remains synchronous.",
        "code",
        claim_type="implementation",
    )
    disabled = _claim(
        "checkout",
        "Async behavior exists behind a disabled flag.",
        "code",
        claim_type="implementation",
    )

    future_result = DriftClassificationService(_settings()).classify(
        match_claim_candidates([future], [current], evidence)[0], evidence
    )
    disabled_result = DriftClassificationService(_settings()).classify(
        match_claim_candidates([_claim("checkout", "Checkout is synchronous.", "doc")], [disabled], evidence)[0],
        evidence,
    )

    assert future_result.relationship == "unrelated"
    assert future_result.is_actionable is False
    assert disabled_result.relationship == "ambiguous"
    assert disabled_result.missing_evidence == ["active runtime behavior"]


def test_pipeline_checks_ranked_candidates_until_one_is_actionable() -> None:
    evidence = [
        _evidence("doc", "google_doc", "Payment processing", "chars:1-20"),
        _evidence("code", "github_pr", "payment_api.py", "file:payment_api.py:lines:1-20"),
    ]
    compatible = match_claim_candidates(
        [_claim("checkout response", "Successful checkout returns HTTP 200.", "doc")],
        [_claim("checkout validation", "Missing keys return HTTP 400.", "code")],
        evidence,
    )[0]
    contradictory = match_claim_candidates(
        [_claim("checkout response", "Successful checkout returns HTTP 200.", "doc")],
        [
            _claim(
                "checkout response",
                "Accepted checkout returns HTTP 202 with a pending state.",
                "code",
            )
        ],
        evidence,
    )[0]
    classifier = FakeClassifier(
        [
            _assessment(actionable=False, canonical=None),
            _assessment(actionable=True, canonical="Checkout returns HTTP 202."),
        ]
    )

    selected = _select_actionable_candidate(
        [compatible, contradictory], classifier, evidence
    )

    assert selected is not None
    assert selected[0] == contradictory
    assert selected[1].proposed_canonical_statement == "Checkout returns HTTP 202."
    assert classifier.calls == 2


def test_candidate_matching_prioritizes_core_async_conflict_over_conditional_400() -> None:
    evidence = [
        _evidence("doc-core", "google_doc", "Payment processing", "chars:1-100"),
        _evidence("doc-status", "google_doc", "Response model", "chars:101-140"),
        _evidence("code", "github_pr", "payment_api.py", "file:payment_api.py:lines:1-40"),
    ]
    documents = [
        _claim(
            "payment processing",
            "Checkout calls the provider synchronously before responding.",
            "doc-core",
        ),
        _claim(
            "successful checkout response",
            "A successful checkout response is HTTP 200.",
            "doc-status",
        ),
    ]
    implementations = [
        _claim(
            "checkout validation",
            "Checkout returns HTTP 400 if the idempotency key is missing or empty.",
            "code",
            claim_type="implementation",
        ),
        _claim(
            "payment processing",
            "Checkout persists a pending payment and enqueues a background worker.",
            "code",
            claim_type="implementation",
        ),
    ]

    candidates = match_claim_candidates(documents, implementations, evidence)

    assert "synchronously" in candidates[0].document_claim.statement
    assert "pending payment" in candidates[0].implementation_claim.statement


class FakeClassifier:
    def __init__(self, results: list[DriftAssessment]):
        self.results = iter(results)
        self.calls = 0

    def classify(self, *_: object) -> DriftAssessment:
        self.calls += 1
        return next(self.results)


def _assessment(*, actionable: bool, canonical: str | None) -> DriftAssessment:
    return DriftAssessment(
        relationship="stale_documentation" if actionable else "supports",
        is_actionable=actionable,
        severity="high" if actionable else "low",
        confidence=0.9,
        concise_reason="Grounded test assessment.",
        evidence_ids=["doc", "code"],
        proposed_canonical_statement=canonical,
    )


def _settings() -> Settings:
    return Settings(_env_file=None, demo_mode=True, mistral_api_key=None)


def _claim(
    subject: str,
    statement: str,
    evidence_id: str,
    *,
    claim_type: str = "current_state",
) -> AtomicClaim:
    return AtomicClaim(
        subject=subject,
        statement=statement,
        claim_type=claim_type,
        status="observed",
        confidence=1,
        evidence_ids=[evidence_id],
    )


def _evidence(
    evidence_id: str, source_type: str, heading: str, locator: str
) -> EvidenceSpan:
    return EvidenceSpan(
        id=evidence_id,
        source_id=f"source:{evidence_id}",
        source_type=source_type,
        source_version="v1",
        locator=locator,
        heading_path=[heading],
        observed_at=OBSERVED_AT,
        content=heading,
    )
