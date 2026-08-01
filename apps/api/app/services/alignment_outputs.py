import json
from collections.abc import Iterable
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    ClaimCandidate,
    DeveloperExplanation,
    DocumentPatchProposal,
    DriftAssessment,
    EvidenceSpan,
    PatchOperation,
    PMExplanation,
    RoleSpecificExplanation,
)
from apps.api.app.services.evidence import EvidenceRegistry
from apps.api.app.services.mistral_gateway import MistralGateway

ROOT = Path(__file__).resolve().parents[4]


class AlignmentOutputUnavailable(RuntimeError):
    pass


class AlignmentOutputService:
    def __init__(self, settings: Settings, *, gateway: MistralGateway | None = None):
        self.settings = settings
        self.gateway = gateway
        if self.gateway is None and settings.mistral_api_key:
            self.gateway = MistralGateway(settings)

    def generate_explanations(
        self,
        candidate: ClaimCandidate,
        assessment: DriftAssessment,
        evidence: Iterable[EvidenceSpan],
    ) -> RoleSpecificExplanation:
        relevant = _validated_relevant_evidence(candidate, assessment, evidence)
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise AlignmentOutputUnavailable("Mistral is required outside demo mode")
            return _demo_explanations(candidate, assessment)
        return self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_fast,
            system=_prompt("05_ROLE_TRANSLATION.md"),
            user=_payload(candidate, assessment, relevant),
            schema=RoleSpecificExplanation,
            evidence=relevant,
        )

    def propose_patch(
        self,
        candidate: ClaimCandidate,
        assessment: DriftAssessment,
        evidence: Iterable[EvidenceSpan],
    ) -> DocumentPatchProposal:
        relevant = _validated_relevant_evidence(candidate, assessment, evidence)
        document_span = _document_span(candidate, relevant)
        if not assessment.is_actionable or not assessment.proposed_canonical_statement:
            raise AlignmentOutputUnavailable("No actionable canonical statement is available")
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise AlignmentOutputUnavailable("Mistral is required outside demo mode")
            return _demo_patch(candidate, assessment, document_span)
        proposed = self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_fast,
            system=_prompt("06_PATCH_PROPOSAL.md"),
            user=_payload(candidate, assessment, relevant),
            schema=DocumentPatchProposal,
            evidence=relevant,
        )
        return _ground_live_patch(proposed, assessment, document_span)


def _demo_explanations(
    candidate: ClaimCandidate, assessment: DriftAssessment
) -> RoleSpecificExplanation:
    evidence_ids = list(dict.fromkeys(assessment.evidence_ids))
    return RoleSpecificExplanation(
        pm=PMExplanation(
            what_changed=(
                "Checkout now acknowledges the request before provider processing finishes and "
                "shows a pending payment state."
            ),
            why_it_matters=(
                "The shared architecture description currently tells readers that payment finishes "
                "inside the checkout request, which no longer matches the cited implementation."
            ),
            impacts=["Checkout responses now use HTTP 202 with a pending payment state."],
            decision_needed="Confirm the customer-facing message for a background payment failure.",
            risks=[],
            glossary={"HTTP 202": "The request was accepted but processing is not yet complete."},
        ),
        developer=DeveloperExplanation(
            technical_change=candidate.implementation_claim.statement,
            affected_files_and_symbols=[
                "payment_api.py: checkout",
                "payment_worker.py: run_payment_job",
            ],
            stale_claim=candidate.document_claim.statement,
            rollout_or_edge_cases=["PaymentJob records provider success or failure after checkout."],
            verification_needed=["Confirm background-failure customer messaging."],
        ),
        evidence_ids=evidence_ids,
    )


def _demo_patch(
    candidate: ClaimCandidate,
    assessment: DriftAssessment,
    document_span: EvidenceSpan,
) -> DocumentPatchProposal:
    original_text = document_span.content.split("\n")[-1]
    line_end = document_span.locator.rsplit("-", 1)[-1]
    locator = f"lines:{line_end}-{line_end}"
    return DocumentPatchProposal(
        target_artifact_id=document_span.source_id,
        expected_revision=document_span.source_version,
        operations=[
            PatchOperation(
                operation="replace_range",
                locator=locator,
                original_text=original_text,
                replacement_text=assessment.proposed_canonical_statement or "",
                evidence_ids=list(dict.fromkeys(assessment.evidence_ids)),
            )
        ],
        rationale=(
            "Replace the stale synchronous-processing paragraph with the smallest statement that "
            "matches the cited checkout handler and worker evidence."
        ),
        evidence_ids=list(dict.fromkeys(assessment.evidence_ids)),
        unresolved_items=["Customer-facing messaging for background payment failure."],
        confidence=min(candidate.score + 0.3, 1.0),
    )


def _ground_live_patch(
    proposed: DocumentPatchProposal,
    assessment: DriftAssessment,
    document_span: EvidenceSpan,
) -> DocumentPatchProposal:
    if document_span.source_type != "google_doc":
        raise AlignmentOutputUnavailable("Live document patching requires Google Docs evidence")
    if not document_span.locator.startswith("chars:") or "-" not in document_span.locator:
        raise AlignmentOutputUnavailable("Google Docs evidence has no character range")

    body_lines = [line for line in document_span.content.splitlines() if line.strip()]
    if len(body_lines) < 2:
        raise AlignmentOutputUnavailable("Google Docs evidence has no replaceable body paragraph")
    original_text = body_lines[-1]
    _, end_text = document_span.locator.removeprefix("chars:").split("-", 1)
    span_end = int(end_text)
    target_end = span_end - 1  # Preserve the paragraph-ending newline.
    target_start = target_end - _utf16_length(original_text)
    if target_start < 1 or target_end <= target_start:
        raise AlignmentOutputUnavailable("Google Docs evidence range is invalid")

    evidence_ids = list(dict.fromkeys(proposed.evidence_ids))
    operation_ids = list(dict.fromkeys(assessment.evidence_ids))
    return proposed.model_copy(
        update={
            "target_artifact_id": document_span.source_id.removeprefix("gdoc:"),
            "expected_revision": document_span.source_version,
            "operations": [
                PatchOperation(
                    operation="replace_range",
                    locator=f"chars:{target_start}-{target_end}",
                    original_text=original_text,
                    replacement_text=assessment.proposed_canonical_statement or "",
                    evidence_ids=operation_ids,
                )
            ],
            "evidence_ids": evidence_ids,
        }
    )


def _utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _validated_relevant_evidence(
    candidate: ClaimCandidate,
    assessment: DriftAssessment,
    evidence: Iterable[EvidenceSpan],
) -> list[EvidenceSpan]:
    spans = list(evidence)
    registry = EvidenceRegistry(spans)
    ids = list(
        dict.fromkeys(
            candidate.document_claim.evidence_ids
            + candidate.implementation_claim.evidence_ids
            + assessment.evidence_ids
        )
    )
    registry.validate(ids)
    return [item for item in spans if item.id in ids]


def _document_span(
    candidate: ClaimCandidate, evidence: list[EvidenceSpan]
) -> EvidenceSpan:
    document_ids = set(candidate.document_claim.evidence_ids)
    try:
        return next(item for item in evidence if item.id in document_ids)
    except StopIteration as exc:
        raise AlignmentOutputUnavailable("Document evidence is unavailable for patching") from exc


def _prompt(filename: str) -> str:
    common = (ROOT / "prompts" / "00_COMMON_RULES.md").read_text(encoding="utf-8")
    specific = (ROOT / "prompts" / filename).read_text(encoding="utf-8")
    return f"{common}\n\n{specific}"


def _payload(
    candidate: ClaimCandidate,
    assessment: DriftAssessment,
    evidence: list[EvidenceSpan],
) -> str:
    return json.dumps(
        {
            "candidate": candidate.model_dump(mode="json"),
            "assessment": assessment.model_dump(mode="json"),
            "untrusted_evidence": [item.model_dump(mode="json") for item in evidence],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
