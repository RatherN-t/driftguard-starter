import json
import re
from collections.abc import Iterable
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    AtomicClaim,
    ClaimCandidate,
    DriftAssessment,
    EvidenceSpan,
)
from apps.api.app.services.evidence import EvidenceRegistry
from apps.api.app.services.mistral_gateway import MistralGateway

ROOT = Path(__file__).resolve().parents[4]
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]+")
_STOPWORDS = {
    "after",
    "and",
    "before",
    "from",
    "into",
    "only",
    "that",
    "the",
    "then",
    "this",
    "using",
    "with",
}
_ALIASES = {
    "api": "endpoint",
    "checkout": "checkout",
    "charge": "payment",
    "charging": "payment",
    "handler": "endpoint",
    "job": "worker",
    "payments": "payment",
    "processing": "process",
    "provider": "payment",
    "queue": "worker",
    "synchronously": "synchronous",
}


class DriftClassificationUnavailable(RuntimeError):
    pass


def match_claim_candidates(
    document_claims: Iterable[AtomicClaim],
    implementation_claims: Iterable[AtomicClaim],
    evidence: Iterable[EvidenceSpan],
    *,
    limit: int = 5,
) -> list[ClaimCandidate]:
    if limit < 1:
        raise ValueError("Candidate limit must be positive")
    registry = EvidenceRegistry(evidence)
    candidates: list[ClaimCandidate] = []
    for document_claim in document_claims:
        registry.validate(document_claim.evidence_ids)
        for implementation_claim in implementation_claims:
            registry.validate(implementation_claim.evidence_ids)
            document_terms = _claim_terms(document_claim)
            implementation_terms = _claim_terms(implementation_claim)
            shared = sorted(document_terms & implementation_terms)
            context_terms = sorted(
                _context_terms(document_claim, registry)
                & _context_terms(implementation_claim, registry)
            )
            subject_overlap = _overlap(
                _terms(document_claim.subject), _terms(implementation_claim.subject)
            )
            statement_overlap = _overlap(document_terms, implementation_terms)
            context_overlap = _overlap(
                _context_terms(document_claim, registry),
                _context_terms(implementation_claim, registry),
            )
            score = min(
                1.0,
                max(
                    0.0,
                    round(
                        0.45 * subject_overlap
                        + 0.35 * statement_overlap
                        + 0.20 * context_overlap
                        + _change_signal(document_claim, implementation_claim),
                        6,
                    ),
                ),
            )
            candidates.append(
                ClaimCandidate(
                    document_claim=document_claim,
                    implementation_claim=implementation_claim,
                    score=score,
                    shared_terms=shared,
                    context_terms=context_terms,
                )
            )
    return sorted(candidates, key=lambda item: (-item.score, item.document_claim.statement))[:limit]


class DriftClassificationService:
    def __init__(self, settings: Settings, *, gateway: MistralGateway | None = None):
        self.settings = settings
        self.gateway = gateway
        if self.gateway is None and settings.mistral_api_key:
            self.gateway = MistralGateway(settings)

    def classify(
        self, candidate: ClaimCandidate, evidence: Iterable[EvidenceSpan]
    ) -> DriftAssessment:
        spans = list(evidence)
        relevant_ids = _candidate_evidence_ids(candidate)
        registry = EvidenceRegistry(spans)
        registry.validate(relevant_ids)
        relevant = [item for item in spans if item.id in relevant_ids]
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise DriftClassificationUnavailable("Mistral is required outside demo mode")
            result = _deterministic_demo_assessment(candidate, relevant_ids)
            registry.validate(result.evidence_ids)
            return result
        prompt = (ROOT / "prompts" / "00_COMMON_RULES.md").read_text(encoding="utf-8")
        prompt += "\n\n" + (ROOT / "prompts" / "04_DRIFT_JUDGE.md").read_text(
            encoding="utf-8"
        )
        return self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_deep,
            system=prompt,
            user=json.dumps(
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "untrusted_evidence": [item.model_dump(mode="json") for item in relevant],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=DriftAssessment,
            evidence=relevant,
        )


def _deterministic_demo_assessment(
    candidate: ClaimCandidate, evidence_ids: list[str]
) -> DriftAssessment:
    document = candidate.document_claim
    implementation = candidate.implementation_claim
    combined = f"{document.statement} {implementation.statement}".lower()

    if "disabled flag" in combined or "flag" in combined and "disabled" in combined:
        relationship = "ambiguous"
        actionable = False
        severity = "low"
        confidence = 0.75
        reason = "The implementation evidence describes disabled behavior, so active drift is uncertain."
        canonical = None
    elif document.claim_type == "future_state":
        relationship = "unrelated"
        actionable = False
        severity = "low"
        confidence = 0.9
        reason = "A future-state document claim is not contradicted solely by current implementation."
        canonical = None
    elif document.claim_type == "requirement":
        relationship = "contradicts"
        actionable = True
        severity = "high"
        confidence = 0.9
        reason = "Observed implementation conflicts with a documented requirement and needs review."
        canonical = None
    elif "does not mention" in combined and (
        "requires" in combined or "stores" in combined or "now" in combined
    ):
        relationship = "undocumented_implementation"
        actionable = True
        severity = "medium"
        confidence = 0.92
        reason = "Observed implementation behavior is absent from the current documentation."
        canonical = implementation.statement
    elif "synchronous" in combined and ("http 202" in combined or "pending" in combined):
        relationship = "stale_documentation"
        actionable = True
        severity = "high"
        confidence = 0.98
        reason = (
            "The document describes synchronous provider confirmation before HTTP 200, while the "
            "implementation returns HTTP 202 with a pending payment and background worker."
        )
        canonical = (
            "Checkout creates a pending payment, enqueues PaymentJob, returns HTTP 202, and the "
            "background worker completes provider processing."
        )
    elif (
        _terms(document.statement) == _terms(implementation.statement)
        or "no behavior change" in combined
        or "identical behavior" in combined
        or "production code unchanged" in combined
    ):
        relationship = "supports"
        actionable = False
        severity = "low"
        confidence = 0.9
        reason = "The supplied implementation evidence supports the documented behavior."
        canonical = None
    else:
        relationship = "ambiguous"
        actionable = False
        severity = "medium"
        confidence = 0.5
        reason = "The available evidence is insufficient to classify the relationship confidently."
        canonical = None

    return DriftAssessment(
        relationship=relationship,
        is_actionable=actionable,
        severity=severity,
        confidence=confidence,
        concise_reason=reason,
        evidence_ids=evidence_ids,
        missing_evidence=[] if relationship != "ambiguous" else ["active runtime behavior"],
        recommended_reviewers=["product manager", "technical lead"] if actionable else [],
        proposed_canonical_statement=canonical,
    )


def _candidate_evidence_ids(candidate: ClaimCandidate) -> list[str]:
    return list(
        dict.fromkeys(
            candidate.document_claim.evidence_ids
            + candidate.implementation_claim.evidence_ids
        )
    )


def _claim_terms(claim: AtomicClaim) -> set[str]:
    return _terms(" ".join(filter(None, (claim.subject, claim.statement, claim.scope))))


def _context_terms(claim: AtomicClaim, registry: EvidenceRegistry) -> set[str]:
    context: list[str] = []
    for evidence_id in claim.evidence_ids:
        span = registry.get(evidence_id)
        context.extend(span.heading_path)
        context.append(span.locator)
    return _terms(" ".join(context))


def _terms(value: str) -> set[str]:
    terms = set()
    for match in _TOKEN.findall(value):
        term = match.lower()
        if term in _STOPWORDS:
            continue
        terms.add(_ALIASES.get(term, term))
    return terms


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _change_signal(document: AtomicClaim, implementation: AtomicClaim) -> float:
    documented = document.statement.lower()
    implemented = implementation.statement.lower()
    signal = 0.0

    if "synchronous" in documented and any(
        term in implemented for term in ("asynchronous", "background", "enqueue", "pending")
    ):
        signal += 0.35
    if "no" in documented and "pending" in documented and "pending" in implemented:
        signal += 0.25
    if "http 200" in documented and "http 202" in implemented:
        signal += 0.25
    if (
        "does not" in documented
        and "idempotency" in documented
        and "requires" in implemented
        and "idempotency" in implemented
    ):
        signal += 0.25
    if (
        "successful" in documented
        and "http 400" in implemented
        and any(term in implemented for term in ("missing", "empty", "invalid"))
    ):
        signal -= 0.30
    return signal
