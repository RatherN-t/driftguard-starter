from collections.abc import Iterable
from typing import TypeVar

import httpx
from mistralai.client import Mistral
from pydantic import BaseModel, ValidationError

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import EvidenceSpan
from apps.api.app.services.evidence import EvidenceRegistry

T = TypeVar("T", bound=BaseModel)


class MistralGatewayError(RuntimeError):
    pass


class MistralStructuredOutputError(MistralGatewayError):
    pass


class MistralGateway:
    """Narrow structured-output boundary with sanitized, bounded retries."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: object | None = None,
        max_attempts: int = 2,
    ):
        if max_attempts not in {1, 2, 3}:
            raise ValueError("max_attempts must be between 1 and 3")
        if client is None and not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")
        self.client = client or Mistral(api_key=settings.mistral_api_key.get_secret_value())
        self.settings = settings
        self.max_attempts = max_attempts

    def parse(self, *, model: str, system: str, user: str, schema: type[T]) -> T:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.chat.parse(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": _repair_instruction(system, attempt),
                        },
                        {"role": "user", "content": user},
                    ],
                    response_format=schema,
                    temperature=0,
                )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise MistralStructuredOutputError(
                        "Mistral returned no parsed structured output"
                    )
                return parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
            except (MistralStructuredOutputError, ValidationError) as exc:
                if attempt == self.max_attempts:
                    raise MistralStructuredOutputError(
                        "Mistral did not return valid structured output"
                    ) from exc
            except Exception as exc:
                if attempt == self.max_attempts or not _is_transient(exc):
                    raise MistralGatewayError("Mistral structured-output request failed") from exc
        raise AssertionError("unreachable")

    def parse_with_evidence(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        evidence: Iterable[EvidenceSpan],
    ) -> T:
        spans = list(evidence)
        registry = EvidenceRegistry(spans)
        aliases = {span.id: f"EVIDENCE_{index}" for index, span in enumerate(spans, start=1)}
        aliased_user = _replace_evidence_ids(user, aliases)
        parsed = self.parse(model=model, system=system, user=aliased_user, schema=schema)
        parsed = schema.model_validate(_restore_evidence_ids(parsed.model_dump(), aliases))
        registry.validate(collect_evidence_ids(parsed))
        return parsed


def collect_evidence_ids(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, BaseModel):
        return collect_evidence_ids(value.model_dump())
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_ids" and isinstance(item, list):
                found.extend(candidate for candidate in item if isinstance(candidate, str))
            else:
                found.extend(collect_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect_evidence_ids(item))
    return found


def _replace_evidence_ids(user: str, aliases: dict[str, str]) -> str:
    for evidence_id in sorted(aliases, key=len, reverse=True):
        user = user.replace(evidence_id, aliases[evidence_id])
    return user


def _restore_evidence_ids(value: object, aliases: dict[str, str]) -> object:
    originals = {alias: evidence_id for evidence_id, alias in aliases.items()}
    if isinstance(value, str):
        return originals.get(value, value)
    if isinstance(value, dict):
        return {key: _restore_evidence_ids(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_evidence_ids(item, aliases) for item in value]
    return value


def _repair_instruction(system: str, attempt: int) -> str:
    if attempt == 1:
        return system
    return (
        f"{system}\n\nYour previous response did not satisfy the required schema. "
        "Return only a schema-valid structured response using supplied evidence IDs."
    )


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or isinstance(status_code, int) and status_code >= 500
