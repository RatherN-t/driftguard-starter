import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path

from mistralai.client import Mistral

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import (
    DecisionExtractionResult,
    DecisionItem,
    EvidenceSpan,
    TranscriptResult,
    TranscriptSegment,
)
from apps.api.app.services.document_chunking import deterministic_evidence_id
from apps.api.app.services.evidence import EvidenceRegistry
from apps.api.app.services.mistral_gateway import MistralGateway

ROOT = Path(__file__).resolve().parents[4]
_TEXT_SEGMENT = re.compile(
    r"^\[(?P<minutes>\d{2}):(?P<seconds>\d{2})\]\s*(?P<speaker>[^:]+):\s*(?P<text>.+)$"
)


class TranscriptionUnavailable(RuntimeError):
    pass


class VoxtralTranscriptionService:
    def __init__(self, settings: Settings, *, client: object | None = None):
        if client is None and not settings.mistral_api_key:
            raise TranscriptionUnavailable("MISTRAL_API_KEY is required for audio transcription")
        self.settings = settings
        self.client = client or Mistral(api_key=settings.mistral_api_key.get_secret_value())

    def transcribe(self, *, filename: str, content: bytes) -> TranscriptResult:
        if not content:
            raise ValueError("Audio file is empty")
        if len(content) > self.settings.audio_max_bytes:
            raise ValueError("Audio file exceeds the configured size limit")
        try:
            response = self.client.audio.transcriptions.complete(
                model=self.settings.mistral_transcribe_model,
                file={"content": io.BytesIO(content), "file_name": filename},
                diarize=True,
                timestamp_granularities=["segment"],
                context_bias=[
                    "DriftGuard",
                    "PaymentJob",
                    "idempotency",
                    "checkout",
                ],
            )
        except Exception as exc:
            raise TranscriptionUnavailable("Voxtral transcription failed") from exc
        return _transcript_result(response, self.settings.mistral_transcribe_model)


class DecisionExtractionService:
    def __init__(self, settings: Settings, *, gateway: MistralGateway | None = None):
        self.settings = settings
        self.gateway = gateway
        if self.gateway is None and settings.mistral_api_key:
            self.gateway = MistralGateway(settings)

    def extract(self, evidence: list[EvidenceSpan]) -> DecisionExtractionResult:
        if self.gateway is None:
            if not self.settings.demo_mode:
                raise TranscriptionUnavailable("Mistral is required outside demo mode")
            return _demo_decisions(evidence)
        common = (ROOT / "prompts" / "00_COMMON_RULES.md").read_text(encoding="utf-8")
        prompt = (ROOT / "prompts" / "03_TRANSCRIPT_DECISIONS.md").read_text(
            encoding="utf-8"
        )
        return self.gateway.parse_with_evidence(
            model=self.settings.mistral_model_fast,
            system=f"{common}\n\n{prompt}",
            user=json.dumps(
                {"untrusted_evidence": [item.model_dump(mode="json") for item in evidence]},
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=DecisionExtractionResult,
            evidence=evidence,
        )


def parse_text_transcript(text: str, *, model: str = "text_fixture") -> TranscriptResult:
    parsed: list[TranscriptSegment] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _TEXT_SEGMENT.fullmatch(line.strip())
        if match is None:
            raise ValueError("Transcript lines must use [MM:SS] Speaker: text format")
        start = int(match["minutes"]) * 60 + int(match["seconds"])
        parsed.append(
            TranscriptSegment(
                speaker=match["speaker"].strip(),
                start_seconds=float(start),
                text=match["text"].strip(),
            )
        )
    if not parsed:
        raise ValueError("Transcript contains no timestamped segments")
    for index, segment in enumerate(parsed[:-1]):
        parsed[index] = segment.model_copy(
            update={"end_seconds": parsed[index + 1].start_seconds}
        )
    return TranscriptResult(text=text.strip(), segments=parsed, model=model)


def transcript_evidence(
    transcript: TranscriptResult,
    *,
    source_id: str,
    observed_at: datetime,
    source_uri: str | None = None,
) -> list[EvidenceSpan]:
    source_version = "sha256:" + hashlib.sha256(
        transcript.text.replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()
    spans = []
    for segment in transcript.segments:
        end = "end" if segment.end_seconds is None else _time_token(segment.end_seconds)
        locator = f"time:{_time_token(segment.start_seconds)}-{end}"
        content = f"{segment.speaker}: {segment.text}"
        spans.append(
            EvidenceSpan(
                id=deterministic_evidence_id(
                    source_id=source_id,
                    source_version=source_version,
                    locator=locator,
                    normalized_content=content,
                ),
                source_id=source_id,
                source_type="meeting_transcript",
                source_uri=source_uri,
                source_version=source_version,
                locator=locator,
                heading_path=["Meeting transcript", segment.speaker],
                observed_at=observed_at,
                content=content,
            )
        )
    return EvidenceRegistry(spans).all()


def _demo_decisions(evidence: list[EvidenceSpan]) -> DecisionExtractionResult:
    approval = _find(evidence, "I approve that approach")
    implementation = _find(evidence, "return 202")
    unresolved = _find(evidence, "customer message is unresolved")
    support = _find(evidence, "what the customer sees")
    result = DecisionExtractionResult(
        decisions=[
            DecisionItem(
                title="Adopt asynchronous checkout payment processing",
                statement=(
                    "For this release, checkout will return HTTP 202, create a pending payment, "
                    "enqueue PaymentJob, and let the worker update final state."
                ),
                status="confirmed",
                owner="Priya (Product Manager)",
                confidence=1,
                evidence_ids=[implementation.id, approval.id],
            )
        ],
        unresolved_questions=[
            DecisionItem(
                title="Background payment failure message",
                statement="The customer-facing message for background payment failure is unresolved.",
                status="ambiguous",
                owner="Priya",
                confidence=1,
                evidence_ids=[support.id, unresolved.id],
            )
        ],
        action_items=[
            DecisionItem(
                title="Update architecture documentation",
                statement="Explain asynchronous processing in the architecture documentation before launch.",
                status="confirmed",
                owner="Engineering",
                confidence=1,
                evidence_ids=[approval.id],
            )
        ],
    )
    registry = EvidenceRegistry(evidence)
    for item in result.decisions + result.unresolved_questions + result.action_items:
        registry.validate(item.evidence_ids)
    return result


def _transcript_result(response: object, model: str) -> TranscriptResult:
    raw_segments = _value(response, "segments") or []
    segments = [
        TranscriptSegment(
            speaker=str(
                _value(item, "speaker_id")
                or _value(item, "speaker")
                or "Unknown speaker"
            ),
            start_seconds=float(_value(item, "start") or 0),
            end_seconds=(
                float(_value(item, "end")) if _value(item, "end") is not None else None
            ),
            text=str(_value(item, "text") or "").strip(),
        )
        for item in raw_segments
        if str(_value(item, "text") or "").strip()
    ]
    if not segments:
        raise TranscriptionUnavailable("Voxtral returned no timestamped transcript segments")
    return TranscriptResult(
        text=str(_value(response, "text") or "").strip(),
        segments=segments,
        language=_value(response, "language"),
        model=str(_value(response, "model") or model),
    )


def _find(evidence: list[EvidenceSpan], phrase: str) -> EvidenceSpan:
    try:
        return next(item for item in evidence if phrase.lower() in item.content.lower())
    except StopIteration as exc:
        raise TranscriptionUnavailable("Required demo transcript evidence was not found") from exc


def _value(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _time_token(seconds: float) -> str:
    return f"{seconds:g}"
