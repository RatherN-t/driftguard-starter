from datetime import UTC, datetime, timedelta
from pathlib import Path

from apps.api.app.services.document_chunking import (
    DEMO_ARCHITECTURE_SOURCE_ID,
    DEMO_ARCHITECTURE_SOURCE_URI,
    chunk_demo_architecture,
    chunk_markdown_document,
    deterministic_evidence_id,
)

ROOT = Path(__file__).resolve().parents[3]
OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_demo_architecture_preserves_hierarchy_identity_version_and_lines() -> None:
    content = (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8")

    spans = chunk_demo_architecture(content, observed_at=OBSERVED_AT)

    assert len(spans) == 8
    payment = next(span for span in spans if span.heading_path[-1] == "Payment processing")
    assert payment.heading_path == [
        "Checkout and Payments Architecture",
        "Customer-facing contract",
        "Payment processing",
    ]
    assert payment.locator == "lines:16-18"
    assert all(span.source_id == DEMO_ARCHITECTURE_SOURCE_ID for span in spans)
    assert all(span.source_uri == DEMO_ARCHITECTURE_SOURCE_URI for span in spans)
    assert all(span.source_type == "demo_fixture" for span in spans)
    assert all(span.source_version == "fixture-v1" for span in spans)
    assert "synchronously" in payment.content


def test_repeated_processing_has_stable_unique_traceable_ids() -> None:
    content = (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8")

    first = chunk_demo_architecture(content, observed_at=OBSERVED_AT)
    second = chunk_demo_architecture(content, observed_at=OBSERVED_AT + timedelta(hours=1))

    assert [span.id for span in first] == [span.id for span in second]
    assert len({span.id for span in first}) == len(first)
    for span in first:
        assert span.id == deterministic_evidence_id(
            source_id=span.source_id,
            source_version=span.source_version,
            locator=span.locator,
            normalized_content=span.content,
        )
        assert "demo%2Farchitecture_doc.md" in span.id
        assert quote_locator(span.locator) in span.id


def test_changing_one_section_only_changes_that_section_id_at_same_version() -> None:
    original = (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8")
    changed = original.replace("HTTP 200", "HTTP 201", 1)

    before = chunk_demo_architecture(original, observed_at=OBSERVED_AT)
    after = chunk_demo_architecture(changed, observed_at=OBSERVED_AT)

    changed_indexes = [
        index
        for index, (left, right) in enumerate(zip(before, after, strict=True))
        if left.id != right.id
    ]
    assert changed_indexes == [
        next(
            index
            for index, span in enumerate(before)
            if span.heading_path[-1] == "Payment processing"
        )
    ]


def test_source_version_change_changes_all_relevant_ids() -> None:
    content = (ROOT / "demo" / "architecture_doc.md").read_text(encoding="utf-8")

    version_one = chunk_demo_architecture(
        content, observed_at=OBSERVED_AT, source_version="fixture-v1"
    )
    version_two = chunk_demo_architecture(
        content, observed_at=OBSERVED_AT, source_version="fixture-v2"
    )

    assert len(version_one) == len(version_two)
    assert all(left.id != right.id for left, right in zip(version_one, version_two, strict=True))


def test_duplicate_headings_are_unique_by_line_locator() -> None:
    content = """# Service

## Retry
First policy.

## Retry
Second policy.
"""

    spans = chunk_markdown_document(
        content,
        source_id="demo/duplicate.md",
        source_type="demo_fixture",
        source_version="v1",
        observed_at=OBSERVED_AT,
    )

    assert [span.heading_path for span in spans] == [
        ["Service", "Retry"],
        ["Service", "Retry"],
    ]
    assert [span.locator for span in spans] == ["lines:3-4", "lines:6-7"]
    assert spans[0].id != spans[1].id


def test_empty_sections_are_skipped_but_remain_in_child_hierarchy() -> None:
    content = """# Service

## Empty parent

### Factual child
Observed behavior.

## Also empty
"""

    spans = chunk_markdown_document(
        content,
        source_id="demo/empty.md",
        source_type="demo_fixture",
        source_version="v1",
        observed_at=OBSERVED_AT,
    )

    assert len(spans) == 1
    assert spans[0].heading_path == ["Service", "Empty parent", "Factual child"]
    assert spans[0].locator == "lines:5-6"


def quote_locator(locator: str) -> str:
    return locator.replace(":", "%3A")
