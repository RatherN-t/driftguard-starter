from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import EvidenceSpan
from apps.api.app.services.embedding_retrieval import (
    EmbeddingRetrievalUnavailable,
    MistralEmbeddingRetrieval,
)


def test_document_retrieval_uses_mistral_text_model_and_hybrid_scores() -> None:
    client = FakeEmbeddingClient([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    service = MistralEmbeddingRetrieval(_settings(), client=client)

    hits = service.rank(
        "async payment",
        [_span("doc:one", "Async payment processing."), _span("doc:two", "Brand colors.")],
        content_kind="document",
    )

    assert client.calls[0]["model"] == "mistral-embed"
    assert client.calls[0]["inputs"][0] == "async payment"
    assert [hit.evidence_id for hit in hits] == ["doc:one", "doc:two"]
    assert hits[0].lexical_score == 1.0
    assert hits[0].model == "mistral-embed"


def test_code_retrieval_uses_codestral_and_stable_evidence_tiebreak() -> None:
    client = FakeEmbeddingClient([[1.0], [1.0], [1.0]])
    service = MistralEmbeddingRetrieval(_settings(), client=client)

    hits = service.rank(
        "worker",
        [_span("code:z", "queue"), _span("code:a", "queue")],
        content_kind="code",
    )

    assert client.calls[0]["model"] == "codestral-embed"
    assert [hit.evidence_id for hit in hits] == ["code:a", "code:z"]


def test_embeddings_fail_clearly_without_credentials() -> None:
    with pytest.raises(EmbeddingRetrievalUnavailable, match="not configured"):
        MistralEmbeddingRetrieval(Settings(_env_file=None, mistral_api_key=None))


def test_malformed_embedding_response_is_sanitized() -> None:
    service = MistralEmbeddingRetrieval(
        _settings(), client=FakeEmbeddingClient([[1.0], [float("nan")]])
    )
    with pytest.raises(EmbeddingRetrievalUnavailable, match="request failed"):
        service.rank("payment", [_span("doc:one", "payment")], content_kind="document")


def _settings() -> Settings:
    return Settings(_env_file=None, mistral_api_key="safe-test-placeholder")


def _span(evidence_id: str, content: str) -> EvidenceSpan:
    return EvidenceSpan(
        id=evidence_id,
        source_id="demo:test",
        source_type="demo_fixture",
        source_version="v1",
        locator="lines:1-1",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        content=content,
    )


class FakeEmbeddingClient:
    def __init__(self, vectors: list[list[float]]):
        self.vectors = vectors
        self.calls: list[dict[str, object]] = []
        self.embeddings = self

    def create(self, *, model: str, inputs: list[str]):
        self.calls.append({"model": model, "inputs": inputs})
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=vector) for vector in self.vectors]
        )
