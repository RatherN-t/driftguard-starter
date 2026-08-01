from datetime import UTC, datetime
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    AtomicClaim,
    ClaimCandidate,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationReport,
    EvidenceSpan,
)
from apps.api.app.services.document_chunking import deterministic_evidence_id
from apps.api.app.services.drift import DriftClassificationService
from apps.api.app.services.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[4]
GOLD_CASES = ROOT / "evals" / "gold_cases.jsonl"
_OBSERVED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def run_gold_evaluation(
    settings: Settings, *, path: Path = GOLD_CASES
) -> EvaluationReport:
    cases = [
        EvaluationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    classifier = DriftClassificationService(
        settings.model_copy(update={"demo_mode": True, "mistral_api_key": None})
    )
    results = [_evaluate_case(classifier, case) for case in cases]
    exact_matches = sum(
        item.relation_correct and item.actionable_correct for item in results
    )
    predicted_actionable = [item for item in results if item.actual_actionable]
    true_actionable = sum(
        item.expected_actionable and item.actual_actionable
        for item in predicted_actionable
    )
    total = len(results)
    return EvaluationReport(
        provenance={
            "mode": "labelled_fixture",
            "is_demo": True,
            "label": "SEEDED EVALUATION - evals/gold_cases.jsonl",
        },
        total_cases=total,
        exact_matches=exact_matches,
        relation_accuracy=_ratio(
            sum(item.relation_correct for item in results), total
        ),
        actionable_precision=_ratio(true_actionable, len(predicted_actionable)),
        citation_coverage=_ratio(
            sum(item.citation_valid for item in results), total
        ),
        hard_negative_false_positives=sum(
            not item.expected_actionable and item.actual_actionable for item in results
        ),
        cases=results,
    )


def _evaluate_case(
    classifier: DriftClassificationService, case: EvaluationCase
) -> EvaluationCaseResult:
    document_evidence = _evidence(case, "document", case.document_claim)
    code_evidence = _evidence(case, "code", case.code_claim)
    evidence = [document_evidence, code_evidence]
    document_claim = AtomicClaim(
        subject="checkout behavior",
        statement=case.document_claim,
        claim_type=case.document_status,
        status="confirmed" if case.document_status == "requirement" else "observed",
        confidence=1,
        evidence_ids=[document_evidence.id],
    )
    implementation_claim = AtomicClaim(
        subject="checkout behavior",
        statement=case.code_claim,
        claim_type="implementation",
        status="observed",
        confidence=1,
        evidence_ids=[code_evidence.id],
    )
    assessment = classifier.classify(
        ClaimCandidate(
            document_claim=document_claim,
            implementation_claim=implementation_claim,
            score=1,
        ),
        evidence,
    )
    registry = EvidenceRegistry(evidence)
    registry.validate(assessment.evidence_ids)
    return EvaluationCaseResult(
        id=case.id,
        expected_relation=case.expected_relation,
        actual_relation=assessment.relationship,
        expected_actionable=case.expected_actionable,
        actual_actionable=assessment.is_actionable,
        relation_correct=assessment.relationship == case.expected_relation,
        actionable_correct=assessment.is_actionable == case.expected_actionable,
        citation_valid=True,
        evidence_ids=assessment.evidence_ids,
    )


def _evidence(case: EvaluationCase, kind: str, content: str) -> EvidenceSpan:
    source_id = f"eval:{case.id}:{kind}"
    source_version = "gold-v1"
    locator = f"case:{case.id}:{kind}"
    return EvidenceSpan(
        id=deterministic_evidence_id(
            source_id=source_id,
            source_version=source_version,
            locator=locator,
            normalized_content=content,
        ),
        source_id=source_id,
        source_type="labelled_evaluation_fixture",
        source_uri="evals/gold_cases.jsonl",
        source_version=source_version,
        locator=locator,
        observed_at=_OBSERVED_AT,
        content=content,
    )


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0
