from datetime import UTC, datetime, timedelta

import pytest

from apps.api.app.services.google_docs_evidence import normalize_google_document

OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


def test_google_document_preserves_hierarchy_ranges_version_and_identity() -> None:
    spans = normalize_google_document(_document(), observed_at=OBSERVED_AT)

    assert len(spans) == 2
    assert [item.heading_path for item in spans] == [
        ["Architecture", "Payments"],
        ["Architecture", "Duplicates"],
    ]
    assert [item.locator for item in spans] == ["chars:15-45", "chars:45-75"]
    assert all(item.source_id == "gdoc:doc-1" for item in spans)
    assert all(item.source_version == "rev-1" for item in spans)
    assert all(item.source_type == "google_doc" for item in spans)


def test_google_document_ids_are_stable_and_duplicate_headings_are_unique() -> None:
    document = _document(duplicate=True)
    first = normalize_google_document(document, observed_at=OBSERVED_AT)
    second = normalize_google_document(document, observed_at=OBSERVED_AT + timedelta(hours=1))

    assert [item.id for item in first] == [item.id for item in second]
    assert len({item.id for item in first}) == len(first)
    assert first[0].heading_path == first[1].heading_path
    assert first[0].locator != first[1].locator


def test_empty_heading_is_skipped_but_preserved_for_child_hierarchy() -> None:
    document = _document(empty_parent=True)
    spans = normalize_google_document(document, observed_at=OBSERVED_AT)

    assert len(spans) == 1
    assert spans[0].heading_path == ["Architecture", "Payments", "Retries"]


def test_tab_aware_document_uses_the_single_document_tab() -> None:
    document = _document()
    document["tabs"] = [{"documentTab": {"body": document.pop("body")}}]

    spans = normalize_google_document(document, observed_at=OBSERVED_AT)

    assert len(spans) == 2
    assert spans[0].heading_path == ["Architecture", "Payments"]


def test_multiple_google_doc_tabs_fail_instead_of_creating_ambiguous_locators() -> None:
    document = _document()
    body = document.pop("body")
    document["tabs"] = [
        {"documentTab": {"body": body}},
        {"documentTab": {"body": {"content": []}}},
    ]

    with pytest.raises(ValueError, match="one tab"):
        normalize_google_document(document, observed_at=OBSERVED_AT)


def _document(*, duplicate: bool = False, empty_parent: bool = False) -> dict:
    if empty_parent:
        paragraphs = [
            _paragraph(1, 15, "Architecture\n", "TITLE"),
            _paragraph(15, 25, "Payments\n", "HEADING_1"),
            _paragraph(25, 35, "Retries\n", "HEADING_2"),
            _paragraph(35, 55, "Retries happen later.\n", "NORMAL_TEXT"),
        ]
    else:
        second_heading = "Payments\n" if duplicate else "Duplicates\n"
        paragraphs = [
            _paragraph(1, 15, "Architecture\n", "TITLE"),
            _paragraph(15, 25, "Payments\n", "HEADING_1"),
            _paragraph(25, 45, "Provider is synchronous.\n", "NORMAL_TEXT"),
            _paragraph(45, 55, second_heading, "HEADING_1"),
            _paragraph(55, 75, "Clients avoid retries.\n", "NORMAL_TEXT"),
        ]
    return {"documentId": "doc-1", "revisionId": "rev-1", "body": {"content": paragraphs}}


def _paragraph(start: int, end: int, text: str, style: str) -> dict:
    return {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [
                {"startIndex": start, "endIndex": end, "textRun": {"content": text}}
            ],
        },
    }
