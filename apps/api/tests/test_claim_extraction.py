from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.api.app.config import Settings
from apps.api.app.integrations.github_client import parse_pr_url
from apps.api.app.services.claim_extraction import (
    ClaimExtractionService,
    ClaimExtractionUnavailable,
)
from apps.api.app.services.document_chunking import chunk_demo_architecture
from apps.api.app.services.github_evidence import normalize_pull_request_evidence

ROOT = Path(__file__).resolve().parents[3]
OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_demo_fallback_extracts_document_and_code_claims_with_valid_citations() -> None:
    settings = Settings(_env_file=None, demo_mode=True, mistral_api_key=None)
    service = ClaimExtractionService(settings)
    document_evidence = chunk_demo_architecture(
        (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8"),
        observed_at=OBSERVED_AT,
    )
    code_evidence = _demo_code_evidence()

    document = service.extract_document_claims(document_evidence)
    code = service.extract_code_claims(code_evidence)

    payment_evidence = next(
        item for item in document_evidence if "synchronously" in item.content
    )
    assert document.claims[0].evidence_ids == [payment_evidence.id]
    assert set(code.evidence_ids) == {
        item.id for item in code_evidence if item.locator.startswith("file:")
    }
    assert code.affected_files == ["payment_api.py", "payment_worker.py"]


def test_live_mode_without_mistral_key_fails_clearly() -> None:
    settings = Settings(_env_file=None, demo_mode=False, mistral_api_key=None)
    service = ClaimExtractionService(settings)

    with pytest.raises(ClaimExtractionUnavailable, match="Mistral is required"):
        service.extract_document_claims([])


def _demo_code_evidence():
    parsed = parse_pr_url("https://github.com/example/driftguard-demo/pull/7")
    metadata = {
        "number": 7,
        "title": "Async checkout",
        "merge_commit_sha": "demoabc123",
    }
    files = [
        {"filename": "payment_api.py", "status": "modified"},
        {"filename": "payment_worker.py", "status": "added"},
    ]
    full_files = {
        filename: (ROOT / "demo" / "code_after" / filename).read_text(encoding="utf-8")
        for filename in ("payment_api.py", "payment_worker.py")
    }
    return normalize_pull_request_evidence(
        parsed,
        metadata=metadata,
        files=files,
        full_files=full_files,
        observed_at=OBSERVED_AT,
    )
