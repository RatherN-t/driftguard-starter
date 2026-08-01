from datetime import UTC, datetime

import pytest

from apps.api.app.domain.schemas import EvidenceSpan
from apps.api.app.services.evidence import UnknownEvidenceReference, validate_evidence_references


def test_unknown_evidence_is_rejected() -> None:
    evidence = [
        EvidenceSpan(
            id="ev-1",
            source_id="demo/example.md",
            source_type="demo",
            source_version="1",
            locator="lines:1-1",
            observed_at=datetime.now(UTC),
            content="example",
        )
    ]
    with pytest.raises(UnknownEvidenceReference):
        validate_evidence_references(evidence, ["ev-2"])
