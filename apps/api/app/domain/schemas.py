from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

Relation = Literal[
    "supports",
    "contradicts",
    "supersedes",
    "implements",
    "partially_implements",
    "stale_documentation",
    "undocumented_implementation",
    "unimplemented_decision",
    "ambiguous",
    "unrelated",
]


class EvidenceSpan(StrictModel):
    id: str
    source_id: str
    source_type: str
    source_uri: str | None = None
    source_version: str
    locator: str
    heading_path: list[str] = Field(default_factory=list)
    observed_at: datetime
    content: str


class AtomicClaim(StrictModel):
    subject: str
    statement: str
    claim_type: Literal[
        "implementation", "current_state", "future_state", "requirement",
        "policy", "decision", "operation", "timeline", "unknown"
    ]
    status: Literal["observed", "proposed", "confirmed", "rejected", "superseded", "unknown"]
    scope: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)


class DocumentClaimExtraction(StrictModel):
    claims: list[AtomicClaim]
    uncertain_points: list[str] = []


class CodeChangeAnalysis(StrictModel):
    summary: str
    implementation_claims: list[AtomicClaim]
    affected_files: list[str]
    evidence_ids: list[str] = Field(min_length=1)
    feature_flags: list[str] = []
    uncertain_points: list[str] = []


class ClaimCandidate(StrictModel):
    document_claim: AtomicClaim
    implementation_claim: AtomicClaim
    score: float = Field(ge=0, le=1)
    shared_terms: list[str] = Field(default_factory=list)
    context_terms: list[str] = Field(default_factory=list)


class RetrievalHit(StrictModel):
    evidence_id: str
    score: float = Field(ge=0, le=1)
    lexical_score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    model: str


class EvaluationCase(StrictModel):
    id: str
    document_claim: str
    document_status: Literal["current_state", "future_state", "requirement"]
    code_claim: str
    decision: str | None = None
    expected_relation: Relation
    expected_actionable: bool


class EvaluationCaseResult(StrictModel):
    id: str
    expected_relation: Relation
    actual_relation: Relation
    expected_actionable: bool
    actual_actionable: bool
    relation_correct: bool
    actionable_correct: bool
    citation_valid: bool
    evidence_ids: list[str] = Field(min_length=1)


class EvaluationReport(StrictModel):
    provenance: dict[str, str | bool]
    total_cases: int = Field(ge=0)
    exact_matches: int = Field(ge=0)
    relation_accuracy: float = Field(ge=0, le=1)
    actionable_precision: float = Field(ge=0, le=1)
    citation_coverage: float = Field(ge=0, le=1)
    hard_negative_false_positives: int = Field(ge=0)
    cases: list[EvaluationCaseResult]


class DecisionItem(StrictModel):
    title: str
    statement: str
    status: Literal["proposed", "confirmed", "rejected", "deferred", "ambiguous"]
    owner: str | None = None
    conditions: list[str] = []
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)


class DecisionExtractionResult(StrictModel):
    decisions: list[DecisionItem]
    unresolved_questions: list[DecisionItem] = []
    action_items: list[DecisionItem] = []


class TranscriptSegment(StrictModel):
    speaker: str
    start_seconds: float = Field(ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    text: str = Field(min_length=1)


class TranscriptResult(StrictModel):
    text: str
    segments: list[TranscriptSegment] = Field(min_length=1)
    language: str | None = None
    model: str


class TranscriptTextRequest(StrictModel):
    text: str = Field(min_length=1, max_length=500_000)


class TranscriptIngestionResult(StrictModel):
    provenance: dict[str, str | bool]
    transcript: TranscriptResult
    evidence: list[EvidenceSpan] = Field(min_length=1)
    decisions: DecisionExtractionResult


class DriftAssessment(StrictModel):
    relationship: Relation
    is_actionable: bool
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=1)
    concise_reason: str
    evidence_ids: list[str] = Field(min_length=1)
    missing_evidence: list[str] = []
    recommended_reviewers: list[str] = []
    proposed_canonical_statement: str | None = None


class PMExplanation(StrictModel):
    what_changed: str
    why_it_matters: str
    impacts: list[str] = []
    decision_needed: str | None = None
    risks: list[str] = []
    glossary: dict[str, str] = {}


class DeveloperExplanation(StrictModel):
    technical_change: str
    affected_files_and_symbols: list[str] = []
    stale_claim: str
    rollout_or_edge_cases: list[str] = []
    verification_needed: list[str] = []


class RoleSpecificExplanation(StrictModel):
    pm: PMExplanation
    developer: DeveloperExplanation
    evidence_ids: list[str] = Field(min_length=1)


class PatchOperation(StrictModel):
    operation: Literal["replace_range", "insert_after", "comment_only"]
    locator: str
    original_text: str | None = None
    replacement_text: str
    evidence_ids: list[str] = Field(min_length=1)


class DocumentPatchProposal(StrictModel):
    target_artifact_id: str
    expected_revision: str
    operations: list[PatchOperation] = Field(min_length=1)
    rationale: str
    evidence_ids: list[str] = Field(min_length=1)
    unresolved_items: list[str] = []
    confidence: float = Field(ge=0, le=1)


class PendingWriteAction(StrictModel):
    action_type: Literal["google_docs_update", "email"]
    target_uri: str
    expected_version: str | None = None
    payload: dict
    evidence_ids: list[str]
    approved: bool = False


class AlertProvenance(StrictModel):
    mode: Literal["demo_fixture", "live"]
    is_demo: bool
    label: str
    inference_mode: Literal["demo_fixture_rules", "mistral"]
    document_source_id: str
    implementation_source_id: str


class DriftAlert(StrictModel):
    id: str
    status: Literal["pending_review", "approved", "rejected", "applied"]
    title: str
    existing_claim: AtomicClaim
    implementation_claim: AtomicClaim
    document_evidence: list[EvidenceSpan] = Field(min_length=1)
    implementation_evidence: list[EvidenceSpan] = Field(min_length=1)
    classification: DriftAssessment
    confidence: float = Field(ge=0, le=1)
    uncertainty: list[str] = Field(default_factory=list)
    explanations: RoleSpecificExplanation
    proposed_canonical_statement: str
    patch: DocumentPatchProposal
    provenance: AlertProvenance
    created_at: datetime


class SourceLinkSummary(StrictModel):
    role: Literal["document", "repository", "pull_request", "transcript"]
    mode: Literal["demo_fixture", "live"]
    label: str
    uri: str
    source_id: str
    source_version: str
    details: list[str] = Field(default_factory=list)


class AnalysisRunRequest(StrictModel):
    document_url: str = Field(min_length=1, max_length=500)
    repository_url: str = Field(min_length=1, max_length=500)
    pull_request_url: str = Field(min_length=1, max_length=500)
    transcript_text: str | None = Field(default=None, max_length=500_000)
    use_demo_transcript: bool = False


class DocumentChangeView(StrictModel):
    mode: Literal["demo_local_copy", "google_docs"]
    document_label: str
    source_uri: str
    target: str
    source_version: str
    before_content: str
    proposed_content: str
    applied_content: str | None = None
    operations: list[PatchOperation] = Field(min_length=1)


class AnalysisRunResult(StrictModel):
    alert: DriftAlert
    sources: list[SourceLinkSummary] = Field(min_length=3)
    transcript: TranscriptIngestionResult | None = None
    document_change: DocumentChangeView


class ReviewDecisionRequest(StrictModel):
    actor_id: str = Field(min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=2_000)
    reason_code: str | None = Field(default=None, max_length=100)


class FeedbackRequest(StrictModel):
    actor_id: str = Field(min_length=1, max_length=200)
    verdict: Literal["correct", "false_positive", "needs_evidence"]
    comment: str | None = Field(default=None, max_length=2_000)


class FeedbackRecord(StrictModel):
    id: str
    alert_id: str
    actor_id: str
    verdict: Literal["correct", "false_positive", "needs_evidence"]
    comment: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    created_at: datetime


class AuditEvent(StrictModel):
    id: str
    alert_id: str
    actor_id: str
    event_type: Literal["alert_approved", "alert_rejected", "patch_applied"]
    prior_state: Literal["pending_review", "approved", "rejected"]
    new_state: Literal["approved", "rejected", "applied"]
    proposed_patch: DocumentPatchProposal
    evidence_ids: list[str]
    comment: str | None = None
    reason_code: str | None = None
    created_at: datetime


class WriteResult(StrictModel):
    status: Literal["applied"]
    mode: Literal["demo_local_copy", "google_docs"]
    target: str
    revision: str
    audit_event: AuditEvent


class EmailPreview(StrictModel):
    subject: str
    text: str
    audience: list[str]
    evidence_ids: list[str] = Field(min_length=1)


class NotificationRequest(StrictModel):
    actor_id: str = Field(min_length=1, max_length=200)
    recipients: list[str] = Field(min_length=1, max_length=10)


class NotificationResult(StrictModel):
    status: Literal["sent"]
    recipients: list[str]
    deduplication_key: str


class GoogleSyncRequest(StrictModel):
    folder_id: str | None = Field(default=None, min_length=1, max_length=200)


class GitHubPRRequest(StrictModel):
    url: HttpUrl
