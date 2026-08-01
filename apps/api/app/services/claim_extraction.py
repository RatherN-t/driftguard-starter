import json
from collections.abc import Iterable
from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    AtomicClaim,
    CodeChangeAnalysis,
    DocumentClaimExtraction,
    EvidenceSpan,
)
from apps.api.app.services.evidence import EvidenceRegistry
from apps.api.app.services.mistral_gateway import MistralGateway

ROOT = Path(__file__).resolve().parents[4]


class ClaimExtractionUnavailable(RuntimeError):
    pass


class ClaimExtractionService:
    def __init__(self, settings: Settings, *, gateway: MistralGateway | None = None):
        self.settings = settings
        self.gateway = gateway
        if self.gateway is None and settings.mistral_api_key:
            self.gateway = MistralGateway(settings)

    def extract_document_claims(
        self, evidence: Iterable[EvidenceSpan]
    ) -> DocumentClaimExtraction:
        spans = list(evidence)
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise ClaimExtractionUnavailable("Mistral is required outside demo mode")
            return _demo_document_extraction(spans)
        return self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_fast,
            system=_prompt("01_DOCUMENT_CLAIMS.md"),
            user=_evidence_payload(spans),
            schema=DocumentClaimExtraction,
            evidence=spans,
        )

    def extract_code_claims(self, evidence: Iterable[EvidenceSpan]) -> CodeChangeAnalysis:
        spans = list(evidence)
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise ClaimExtractionUnavailable("Mistral is required outside demo mode")
            return _demo_code_extraction(spans)
        return self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_fast,
            system=_prompt("02_CODE_CHANGE.md"),
            user=_evidence_payload(spans),
            schema=CodeChangeAnalysis,
            evidence=spans,
        )


def _demo_document_extraction(evidence: list[EvidenceSpan]) -> DocumentClaimExtraction:
    span = next((item for item in evidence if "synchronously" in item.content), None)
    if span is None or span.source_type != "demo_fixture":
        raise ClaimExtractionUnavailable("Demo document fixture evidence was not found")
    result = DocumentClaimExtraction(
        claims=[
            AtomicClaim(
                subject="checkout payment processing",
                statement=(
                    "The checkout API calls the payment provider synchronously and returns only "
                    "after provider confirmation, using HTTP 200 with no intermediate state."
                ),
                claim_type="current_state",
                status="observed",
                scope="Payment processing",
                confidence=1.0,
                evidence_ids=[span.id],
            )
        ]
    )
    EvidenceRegistry(evidence).validate(result.claims[0].evidence_ids)
    return result


def _demo_code_extraction(evidence: list[EvidenceSpan]) -> CodeChangeAnalysis:
    api = next(
        (
            item
            for item in evidence
            if item.source_type == "github_pr"
            and item.locator.startswith("file:payment_api.py:")
            and "return Response(202" in item.content
        ),
        None,
    )
    worker = next(
        (
            item
            for item in evidence
            if item.source_type == "github_pr"
            and item.locator.startswith("file:payment_worker.py:")
            and "provider.charge" in item.content
        ),
        None,
    )
    if api is None or worker is None:
        raise ClaimExtractionUnavailable("Demo code fixture evidence was not found")
    evidence_ids = [api.id, worker.id]
    result = CodeChangeAnalysis(
        summary=(
            "Checkout now creates a pending payment, enqueues PaymentJob, returns HTTP 202, "
            "and charges the provider in the background worker."
        ),
        implementation_claims=[
            AtomicClaim(
                subject="checkout payment processing",
                statement=(
                    "The checkout handler creates a pending payment, enqueues PaymentJob, returns "
                    "HTTP 202, and the worker performs the provider charge."
                ),
                claim_type="implementation",
                status="observed",
                scope="payment_api.py and payment_worker.py",
                confidence=1.0,
                evidence_ids=evidence_ids,
            )
        ],
        affected_files=["payment_api.py", "payment_worker.py"],
        evidence_ids=evidence_ids,
    )
    EvidenceRegistry(evidence).validate(evidence_ids)
    return result


def _prompt(filename: str) -> str:
    common = (ROOT / "prompts" / "00_COMMON_RULES.md").read_text(encoding="utf-8")
    specific = (ROOT / "prompts" / filename).read_text(encoding="utf-8")
    return f"{common}\n\n{specific}"


def _evidence_payload(evidence: list[EvidenceSpan]) -> str:
    return json.dumps(
        {"untrusted_evidence": [item.model_dump(mode="json") for item in evidence]},
        ensure_ascii=False,
        sort_keys=True,
    )
