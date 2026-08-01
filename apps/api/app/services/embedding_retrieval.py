import math
import re
from collections.abc import Iterable
from typing import Literal

from mistralai.client import Mistral

from apps.api.app.config import Settings
from apps.api.app.domain.schemas import EvidenceSpan, RetrievalHit
from apps.api.app.services.evidence import EvidenceRegistry

ContentKind = Literal["document", "code"]
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]+")


class EmbeddingRetrievalUnavailable(RuntimeError):
    pass


class MistralEmbeddingRetrieval:
    """Hybrid retrieval using deterministic terms and Mistral-only embeddings."""

    def __init__(self, settings: Settings, *, client: object | None = None):
        if client is None and not settings.mistral_api_key:
            raise EmbeddingRetrievalUnavailable("Mistral embeddings are not configured")
        self.settings = settings
        self.client = client or Mistral(
            api_key=settings.mistral_api_key.get_secret_value()
        )

    def rank(
        self,
        query: str,
        evidence: Iterable[EvidenceSpan],
        *,
        content_kind: ContentKind,
        limit: int = 5,
    ) -> list[RetrievalHit]:
        spans = list(evidence)
        if not query.strip():
            raise ValueError("Retrieval query must not be empty")
        if limit < 1:
            raise ValueError("Retrieval limit must be positive")
        EvidenceRegistry(spans)
        if not spans:
            return []

        model = (
            self.settings.mistral_text_embed_model
            if content_kind == "document"
            else self.settings.mistral_code_embed_model
        )
        try:
            response = self.client.embeddings.create(
                model=model,
                inputs=[query, *(span.content for span in spans)],
            )
            vectors = [item.embedding for item in response.data]
            if len(vectors) != len(spans) + 1 or any(vector is None for vector in vectors):
                raise ValueError("Embedding response did not match requested inputs")
            query_vector = _validated_vector(vectors[0])
            content_vectors = [_validated_vector(vector) for vector in vectors[1:]]
        except Exception as exc:
            raise EmbeddingRetrievalUnavailable(
                "Mistral embedding request failed"
            ) from exc

        hits = []
        for span, vector in zip(spans, content_vectors, strict=True):
            lexical = _lexical_overlap(query, span.content)
            semantic = max(0.0, min(1.0, (_cosine(query_vector, vector) + 1) / 2))
            score = round(0.35 * lexical + 0.65 * semantic, 6)
            hits.append(
                RetrievalHit(
                    evidence_id=span.id,
                    score=score,
                    lexical_score=round(lexical, 6),
                    semantic_score=round(semantic, 6),
                    model=model,
                )
            )
        return sorted(hits, key=lambda hit: (-hit.score, hit.evidence_id))[:limit]


def _validated_vector(value: list[float] | None) -> list[float]:
    if not value or not all(math.isfinite(item) for item in value):
        raise ValueError("Embedding vector must contain finite values")
    return value


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions do not match")
    left_norm = math.sqrt(sum(item * item for item in left))
    right_norm = math.sqrt(sum(item * item for item in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )


def _lexical_overlap(query: str, content: str) -> float:
    query_terms = {item.lower() for item in _TOKEN.findall(query)}
    content_terms = {item.lower() for item in _TOKEN.findall(content)}
    if not query_terms:
        return 0.0
    return len(query_terms & content_terms) / len(query_terms)
