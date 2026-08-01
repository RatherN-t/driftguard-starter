from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import AtomicClaim, DocumentClaimExtraction, EvidenceSpan
from apps.api.app.services.evidence import UnknownEvidenceReference
from apps.api.app.services.mistral_gateway import (
    MistralGateway,
    MistralGatewayError,
    MistralStructuredOutputError,
)


def test_gateway_returns_typed_structured_output() -> None:
    expected = _extraction("ev-1")
    client = FakeMistralClient([_response(expected)])
    gateway = MistralGateway(_settings(), client=client)

    result = gateway.parse(
        model="mistral-small-latest",
        system="system",
        user="user",
        schema=DocumentClaimExtraction,
    )

    assert result == expected
    assert client.calls == 1


def test_gateway_retries_transient_failure() -> None:
    request = httpx.Request("POST", "https://api.mistral.ai/chat")
    client = FakeMistralClient([httpx.ReadTimeout("timeout", request=request), _response(_extraction("ev-1"))])
    gateway = MistralGateway(_settings(), client=client)

    result = gateway.parse(
        model="mistral-small-latest",
        system="system",
        user="user",
        schema=DocumentClaimExtraction,
    )

    assert result.claims[0].evidence_ids == ["ev-1"]
    assert client.calls == 2


def test_gateway_retries_missing_parsed_output_for_schema_repair() -> None:
    client = FakeMistralClient([_response(None), _response(_extraction("ev-1"))])
    gateway = MistralGateway(_settings(), client=client)

    gateway.parse(
        model="mistral-small-latest",
        system="system",
        user="user",
        schema=DocumentClaimExtraction,
    )

    assert client.calls == 2
    assert "previous response" in client.system_messages[1].lower()


def test_gateway_does_not_retry_nontransient_failure() -> None:
    client = FakeMistralClient([RuntimeError("bad request")])
    gateway = MistralGateway(_settings(), client=client)

    with pytest.raises(MistralGatewayError):
        gateway.parse(
            model="mistral-small-latest",
            system="system",
            user="user",
            schema=DocumentClaimExtraction,
        )

    assert client.calls == 1


def test_gateway_rejects_repeated_invalid_schema() -> None:
    client = FakeMistralClient([_response(None), _response(None)])
    gateway = MistralGateway(_settings(), client=client)

    with pytest.raises(MistralStructuredOutputError):
        gateway.parse(
            model="mistral-small-latest",
            system="system",
            user="user",
            schema=DocumentClaimExtraction,
        )


def test_gateway_rejects_unknown_evidence_id() -> None:
    client = FakeMistralClient([_response(_extraction("unknown"))])
    gateway = MistralGateway(_settings(), client=client)

    with pytest.raises(UnknownEvidenceReference):
        gateway.parse_with_evidence(
            model="mistral-small-latest",
            system="system",
            user="user",
            schema=DocumentClaimExtraction,
            evidence=[_evidence()],
        )


def test_gateway_uses_short_model_aliases_and_restores_traceable_evidence_ids() -> None:
    evidence = _evidence()
    evidence.id = (
        "evidence:gdoc%3Adoc:very-long-revision:chars%3A1-100:"
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    client = FakeMistralClient([_response(_extraction("EVIDENCE_1"))])
    gateway = MistralGateway(_settings(), client=client)

    result = gateway.parse_with_evidence(
        model="mistral-small-latest",
        system="system",
        user=f'{{"id":"{evidence.id}"}}',
        schema=DocumentClaimExtraction,
        evidence=[evidence],
    )

    assert result.claims[0].evidence_ids == [evidence.id]
    assert "EVIDENCE_1" in client.user_messages[0]
    assert evidence.id not in client.user_messages[0]


class FakeMistralClient:
    def __init__(self, results: list[object]):
        self.results = iter(results)
        self.calls = 0
        self.system_messages: list[str] = []
        self.user_messages: list[str] = []
        self.chat = self

    def parse(self, **kwargs: object) -> object:
        self.calls += 1
        messages = kwargs["messages"]
        self.system_messages.append(messages[0]["content"])
        self.user_messages.append(messages[1]["content"])
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def _response(parsed: object) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))]
    )


def _settings() -> Settings:
    return Settings(_env_file=None, mistral_api_key=None, demo_mode=True)


def _extraction(evidence_id: str) -> DocumentClaimExtraction:
    return DocumentClaimExtraction(
        claims=[
            AtomicClaim(
                subject="checkout",
                statement="Checkout is synchronous.",
                claim_type="current_state",
                status="observed",
                confidence=1,
                evidence_ids=[evidence_id],
            )
        ]
    )


def _evidence() -> EvidenceSpan:
    return EvidenceSpan(
        id="ev-1",
        source_id="demo/doc",
        source_type="demo_fixture",
        source_version="v1",
        locator="lines:1-1",
        observed_at=datetime.now(UTC),
        content="Checkout is synchronous.",
    )
