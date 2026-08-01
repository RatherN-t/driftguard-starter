import json
from datetime import datetime

from apps.api.app.domain.schemas import EvidenceSpan
from apps.api.app.integrations.github_client import ParsedPR
from apps.api.app.services.document_chunking import (
    deterministic_evidence_id,
    normalize_evidence_content,
)
from apps.api.app.services.evidence import EvidenceRegistry


def normalize_pull_request_evidence(
    parsed: ParsedPR,
    *,
    metadata: dict,
    files: list[dict],
    full_files: dict[str, str],
    observed_at: datetime,
) -> list[EvidenceSpan]:
    source_version = selected_sha(metadata)
    source_id = parsed.source_id
    spans = [
        _span(
            source_id=source_id,
            source_version=source_version,
            source_uri=parsed.canonical_url,
            locator="pr:metadata",
            heading_path=[f"Pull request #{parsed.number}", "Metadata"],
            content=_metadata_content(metadata),
            observed_at=observed_at,
        )
    ]

    seen_paths: set[str] = set()
    for file_data in files:
        path = file_data.get("filename")
        if not isinstance(path, str) or not _safe_repository_path(path):
            raise ValueError("Changed-file metadata contains an unsafe or missing filename")
        if path in seen_paths:
            raise ValueError(f"Changed-file metadata contains duplicate path: {path}")
        seen_paths.add(path)

        patch = file_data.get("patch")
        if isinstance(patch, str) and patch.strip():
            spans.append(
                _span(
                    source_id=source_id,
                    source_version=source_version,
                    source_uri=parsed.canonical_url,
                    locator=f"patch:{path}",
                    heading_path=[f"Pull request #{parsed.number}", path, "Patch"],
                    content=patch,
                    observed_at=observed_at,
                )
            )
        else:
            spans.append(
                _span(
                    source_id=source_id,
                    source_version=source_version,
                    source_uri=parsed.canonical_url,
                    locator=f"file-metadata:{path}",
                    heading_path=[f"Pull request #{parsed.number}", path, "Changed file"],
                    content=json.dumps(file_data, sort_keys=True, separators=(",", ":")),
                    observed_at=observed_at,
                )
            )

        full_content = full_files.get(path)
        if full_content is not None:
            line_count = max(1, len(full_content.replace("\r\n", "\n").splitlines()))
            spans.append(
                _span(
                    source_id=source_id,
                    source_version=source_version,
                    source_uri=parsed.canonical_url,
                    locator=f"file:{path}:lines:1-{line_count}",
                    heading_path=[f"Pull request #{parsed.number}", path, "Full file"],
                    content=full_content,
                    observed_at=observed_at,
                )
            )

    unknown_full_files = set(full_files) - seen_paths
    if unknown_full_files:
        raise ValueError(f"Full-file content has no changed-file metadata: {sorted(unknown_full_files)}")

    return EvidenceRegistry(spans).all()


def selected_sha(metadata: dict) -> str:
    merge_sha = metadata.get("merge_commit_sha")
    if isinstance(merge_sha, str) and merge_sha:
        return merge_sha
    head = metadata.get("head")
    if isinstance(head, dict) and isinstance(head.get("sha"), str) and head["sha"]:
        return head["sha"]
    raise ValueError("Pull request metadata has no usable merge or head SHA")


def _metadata_content(metadata: dict) -> str:
    author = metadata.get("user")
    author_login = author.get("login") if isinstance(author, dict) else metadata.get("author")
    selected = {
        "author": author_login,
        "body": metadata.get("body"),
        "merged": metadata.get("merged"),
        "number": metadata.get("number"),
        "state": metadata.get("state"),
        "title": metadata.get("title"),
    }
    return json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _span(
    *,
    source_id: str,
    source_version: str,
    source_uri: str,
    locator: str,
    heading_path: list[str],
    content: str,
    observed_at: datetime,
) -> EvidenceSpan:
    normalized = normalize_evidence_content(content)
    return EvidenceSpan(
        id=deterministic_evidence_id(
            source_id=source_id,
            source_version=source_version,
            locator=locator,
            normalized_content=normalized,
        ),
        source_id=source_id,
        source_type="github_pr",
        source_uri=source_uri,
        source_version=source_version,
        locator=locator,
        heading_path=heading_path,
        observed_at=observed_at,
        content=normalized,
    )


def _safe_repository_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return bool(normalized) and not normalized.startswith("/") and ".." not in normalized.split("/")
