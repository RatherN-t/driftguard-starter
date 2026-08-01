from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.app.config import Settings
from apps.api.app.main import app
from apps.api.app.services.transcripts import (
    DecisionExtractionService,
    VoxtralTranscriptionService,
    parse_text_transcript,
    transcript_evidence,
)

ROOT = Path(__file__).resolve().parents[3]
OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_text_transcript_produces_speaker_timestamp_evidence_and_decisions() -> None:
    text = (ROOT / "demo" / "meeting_transcript.txt").read_text(encoding="utf-8")
    transcript = parse_text_transcript(text)
    evidence = transcript_evidence(
        transcript, source_id="transcript:demo", observed_at=OBSERVED_AT
    )
    decisions = DecisionExtractionService(_settings()).extract(evidence)

    assert len(transcript.segments) == 5
    assert transcript.segments[0].speaker == "Priya (Product Manager)"
    assert transcript.segments[0].start_seconds == 0
    assert transcript.segments[0].end_seconds == 18
    assert evidence[0].locator == "time:0-18"
    assert decisions.decisions[0].status == "confirmed"
    assert decisions.unresolved_questions[0].status == "ambiguous"
    known_ids = {item.id for item in evidence}
    assert set(decisions.decisions[0].evidence_ids) <= known_ids


def test_transcript_evidence_ids_are_deterministic() -> None:
    text = (ROOT / "demo" / "meeting_transcript.txt").read_text(encoding="utf-8")
    transcript = parse_text_transcript(text)

    first = transcript_evidence(
        transcript, source_id="transcript:demo", observed_at=OBSERVED_AT
    )
    second = transcript_evidence(
        transcript,
        source_id="transcript:demo",
        observed_at=OBSERVED_AT + timedelta(hours=1),
    )

    assert [item.id for item in first] == [item.id for item in second]


def test_voxtral_request_uses_diarization_timestamps_and_context_bias() -> None:
    fake = FakeVoxtralClient()
    result = VoxtralTranscriptionService(_settings(), client=fake).transcribe(
        filename="meeting.wav", content=b"audio"
    )

    assert result.segments[0].speaker == "speaker_0"
    assert result.segments[0].start_seconds == 0
    assert fake.kwargs["diarize"] is True
    assert fake.kwargs["timestamp_granularities"] == ["segment"]
    assert "PaymentJob" in fake.kwargs["context_bias"]


def test_text_api_fallback_works_and_audio_without_key_fails_clearly() -> None:
    client = TestClient(app)
    text = (ROOT / "demo" / "meeting_transcript.txt").read_text(encoding="utf-8")

    text_response = client.post("/api/sources/transcript/text", json={"text": text})
    audio_response = client.post(
        "/api/sources/transcript/audio",
        files={"file": ("meeting.wav", b"audio", "audio/wav")},
    )

    assert text_response.status_code == 200
    assert text_response.json()["provenance"]["is_demo"] is True
    assert text_response.json()["decisions"]["decisions"]
    assert audio_response.status_code == 503
    assert "MISTRAL_API_KEY" in audio_response.json()["detail"]


def test_demo_decision_log_endpoint_is_labelled_and_evidence_linked() -> None:
    response = TestClient(app).get("/api/sources/transcript/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["is_demo"] is True
    assert payload["provenance"]["label"].startswith("DEMO DATA")
    known_ids = {item["id"] for item in payload["evidence"]}
    cited_ids = {
        evidence_id
        for group in ("decisions", "unresolved_questions", "action_items")
        for item in payload["decisions"][group]
        for evidence_id in item["evidence_ids"]
    }
    assert cited_ids
    assert cited_ids <= known_ids


class FakeVoxtralClient:
    def __init__(self):
        self.audio = self
        self.transcriptions = self
        self.kwargs: dict = {}

    def complete(self, **kwargs: object):
        self.kwargs = kwargs
        return SimpleNamespace(
            text="Checkout will be asynchronous.",
            language="en",
            model="voxtral-mini-latest",
            segments=[
                SimpleNamespace(
                    speaker_id="speaker_0",
                    start=0,
                    end=2.5,
                    text="Checkout will be asynchronous.",
                )
            ],
        )


def _settings() -> Settings:
    return Settings(_env_file=None, demo_mode=True, mistral_api_key=None)
