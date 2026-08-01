import hashlib
import re
from datetime import datetime
from urllib.parse import quote

from apps.api.app.domain.schemas import EvidenceSpan

DEMO_ARCHITECTURE_SOURCE_ID = "demo/architecture_doc.md"
DEMO_ARCHITECTURE_SOURCE_VERSION = "fixture-v1"
DEMO_ARCHITECTURE_SOURCE_URI = "demo://architecture_doc.md"

_ATX_HEADING = re.compile(
    r"^[ \t]{0,3}(?P<marks>#{1,6})(?:[ \t]+(?P<title>.*?))?[ \t]*$"
)
_CLOSING_MARKS = re.compile(r"[ \t]+#+[ \t]*$")


def normalize_evidence_content(content: str) -> str:
    """Canonicalize newlines and insignificant trailing whitespace for stable IDs."""
    normalized_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized_lines = [line.rstrip() for line in normalized_lines]
    while normalized_lines and not normalized_lines[0]:
        normalized_lines.pop(0)
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def deterministic_evidence_id(
    *,
    source_id: str,
    source_version: str,
    locator: str,
    normalized_content: str,
) -> str:
    """Build a stable, human-traceable ID from the required evidence coordinates."""
    values = {
        "source_id": source_id,
        "source_version": source_version,
        "locator": locator,
        "normalized_content": normalized_content,
    }
    for name, value in values.items():
        if not value:
            raise ValueError(f"{name} must not be empty")

    content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
    encoded_coordinates = ":".join(
        quote(value, safe="") for value in (source_id, source_version, locator)
    )
    return f"evidence:{encoded_coordinates}:{content_hash}"


def chunk_markdown_document(
    content: str,
    *,
    source_id: str,
    source_type: str,
    source_version: str,
    observed_at: datetime,
    source_uri: str | None = None,
) -> list[EvidenceSpan]:
    """Split Markdown at ATX headings and return factual, line-addressable sections."""
    if not source_id:
        raise ValueError("source_id must not be empty")
    if not source_type:
        raise ValueError("source_type must not be empty")
    if not source_version:
        raise ValueError("source_version must not be empty")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")

    canonical_document = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = canonical_document.split("\n")
    if not any(line.strip() for line in lines):
        return []

    sections: list[tuple[int, int, list[str]]] = []
    heading_stack: list[str] = []
    current_start = 0
    current_heading_path: list[str] = []
    current_starts_with_heading = False

    for index, line in enumerate(lines):
        heading = _parse_heading(line)
        if heading is None:
            continue

        if index > current_start or any(item.strip() for item in lines[current_start:index]):
            _append_nonempty_section(
                sections,
                lines,
                current_start,
                index - 1,
                current_heading_path,
                current_starts_with_heading,
            )

        level, title = heading
        heading_stack = heading_stack[: level - 1]
        heading_stack.append(title)
        current_start = index
        current_heading_path = list(heading_stack)
        current_starts_with_heading = True

    _append_nonempty_section(
        sections,
        lines,
        current_start,
        len(lines) - 1,
        current_heading_path,
        current_starts_with_heading,
    )

    evidence: list[EvidenceSpan] = []
    for start, end, heading_path in sections:
        normalized_content = normalize_evidence_content("\n".join(lines[start : end + 1]))
        locator = f"lines:{start + 1}-{end + 1}"
        evidence.append(
            EvidenceSpan(
                id=deterministic_evidence_id(
                    source_id=source_id,
                    source_version=source_version,
                    locator=locator,
                    normalized_content=normalized_content,
                ),
                source_id=source_id,
                source_type=source_type,
                source_uri=source_uri,
                source_version=source_version,
                locator=locator,
                heading_path=heading_path,
                observed_at=observed_at,
                content=normalized_content,
            )
        )
    return evidence


def chunk_demo_architecture(
    content: str,
    *,
    observed_at: datetime,
    source_version: str = DEMO_ARCHITECTURE_SOURCE_VERSION,
) -> list[EvidenceSpan]:
    """Normalize the explicitly labelled local demo architecture fixture."""
    return chunk_markdown_document(
        content,
        source_id=DEMO_ARCHITECTURE_SOURCE_ID,
        source_type="demo_fixture",
        source_version=source_version,
        source_uri=DEMO_ARCHITECTURE_SOURCE_URI,
        observed_at=observed_at,
    )


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = _ATX_HEADING.fullmatch(line)
    if match is None:
        return None
    title = _CLOSING_MARKS.sub("", match.group("title") or "").strip()
    return len(match.group("marks")), title


def _append_nonempty_section(
    sections: list[tuple[int, int, list[str]]],
    lines: list[str],
    start: int,
    end: int,
    heading_path: list[str],
    starts_with_heading: bool,
) -> None:
    while start <= end and not lines[start].strip():
        start += 1
    while end >= start and not lines[end].strip():
        end -= 1
    if start > end:
        return
    if starts_with_heading and not any(line.strip() for line in lines[start + 1 : end + 1]):
        return
    sections.append((start, end, list(heading_path)))
