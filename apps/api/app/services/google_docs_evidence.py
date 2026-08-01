from datetime import datetime

from apps.api.app.domain.schemas import EvidenceSpan
from apps.api.app.integrations.google_docs_client import document_body
from apps.api.app.services.document_chunking import (
    deterministic_evidence_id,
    normalize_evidence_content,
)
from apps.api.app.services.evidence import EvidenceRegistry

_HEADING_LEVELS = {
    "TITLE": 1,
    "HEADING_1": 2,
    "HEADING_2": 3,
    "HEADING_3": 4,
    "HEADING_4": 5,
    "HEADING_5": 6,
    "HEADING_6": 7,
}


def normalize_google_document(
    document: dict,
    *,
    observed_at: datetime,
    source_uri: str | None = None,
) -> list[EvidenceSpan]:
    document_id = document.get("documentId")
    revision = document.get("revisionId")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Google document is missing documentId")
    if not isinstance(revision, str) or not revision:
        raise ValueError("Google document is missing revisionId")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")

    paragraphs = _paragraphs(document)
    sections: list[tuple[int, int, list[str], str]] = []
    hierarchy: list[str] = []
    current: list[tuple[int, int, str]] = []
    current_path: list[str] = []
    current_has_heading = False

    for start, end, text, style in paragraphs:
        level = _HEADING_LEVELS.get(style)
        if level is not None:
            _finish_section(sections, current, current_path, current_has_heading)
            title = normalize_evidence_content(text)
            hierarchy = hierarchy[: level - 1]
            hierarchy.append(title)
            current = [(start, end, text)]
            current_path = list(hierarchy)
            current_has_heading = True
        else:
            current.append((start, end, text))
    _finish_section(sections, current, current_path, current_has_heading)

    source_id = f"gdoc:{document_id}"
    uri = source_uri or f"https://docs.google.com/document/d/{document_id}/edit"
    spans = [
        _span(
            source_id=source_id,
            source_version=revision,
            source_uri=uri,
            start=start,
            end=end,
            heading_path=heading_path,
            content=content,
            observed_at=observed_at,
        )
        for start, end, heading_path, content in sections
    ]
    return EvidenceRegistry(spans).all()


def _paragraphs(document: dict) -> list[tuple[int, int, str, str]]:
    items: list[tuple[int, int, str, str]] = []
    for structural in document_body(document).get("content", []):
        paragraph = structural.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        text = "".join(
            str(element.get("textRun", {}).get("content", ""))
            for element in paragraph.get("elements", [])
            if isinstance(element.get("textRun"), dict)
        )
        start = int(structural.get("startIndex", 0))
        end = int(structural.get("endIndex", start))
        style = str(paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT"))
        if text or end > start:
            items.append((start, end, text, style))
    return items


def _finish_section(
    sections: list[tuple[int, int, list[str], str]],
    current: list[tuple[int, int, str]],
    heading_path: list[str],
    has_heading: bool,
) -> None:
    if not current:
        return
    body = current[1:] if has_heading else current
    if not any(normalize_evidence_content(text) for _, _, text in body):
        return
    content = normalize_evidence_content("".join(text for _, _, text in current))
    if content:
        sections.append((current[0][0], current[-1][1], list(heading_path), content))


def _span(
    *,
    source_id: str,
    source_version: str,
    source_uri: str,
    start: int,
    end: int,
    heading_path: list[str],
    content: str,
    observed_at: datetime,
) -> EvidenceSpan:
    locator = f"chars:{start}-{end}"
    return EvidenceSpan(
        id=deterministic_evidence_id(
            source_id=source_id,
            source_version=source_version,
            locator=locator,
            normalized_content=content,
        ),
        source_id=source_id,
        source_type="google_doc",
        source_uri=source_uri,
        source_version=source_version,
        locator=locator,
        heading_path=heading_path,
        observed_at=observed_at,
        content=content,
    )
