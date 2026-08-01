from datetime import UTC, datetime, timedelta

import pytest

from apps.api.app.integrations.github_client import parse_pr_url
from apps.api.app.services.evidence import (
    DuplicateEvidenceReference,
    EvidenceRegistry,
    UnknownEvidenceReference,
)
from apps.api.app.services.github_evidence import normalize_pull_request_evidence

PARSED = parse_pr_url("https://github.com/acme/payments/pull/42")
OBSERVED_AT = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
METADATA = {
    "number": 42,
    "title": "Async payments",
    "body": "Queue provider work",
    "merged": True,
    "merge_commit_sha": "merge123",
}
FILES = [
    {
        "filename": "src/payment.py",
        "status": "modified",
        "patch": "@@ -1 +1 @@\n-return 200\n+return 202",
    },
    {"filename": "src/worker.py", "status": "added"},
]
FULL_FILES = {
    "src/payment.py": "def checkout():\n    return 202\n",
    "src/worker.py": "def charge():\n    pass\n",
}


def test_normalizes_metadata_patch_file_metadata_and_full_files() -> None:
    spans = _normalize()

    assert len(spans) == 5
    assert [span.locator for span in spans] == [
        "pr:metadata",
        "patch:src/payment.py",
        "file:src/payment.py:lines:1-2",
        "file-metadata:src/worker.py",
        "file:src/worker.py:lines:1-2",
    ]
    assert all(span.source_id == PARSED.source_id for span in spans)
    assert all(span.source_version == "merge123" for span in spans)
    assert all(span.source_type == "github_pr" for span in spans)


def test_normalization_is_deterministic_and_unique() -> None:
    first = _normalize()
    second = _normalize(observed_at=OBSERVED_AT + timedelta(hours=1))

    assert [item.id for item in first] == [item.id for item in second]
    assert len({item.id for item in first}) == len(first)


def test_changed_full_file_only_changes_affected_file_evidence_at_same_version() -> None:
    before = _normalize()
    changed_files = dict(FULL_FILES)
    changed_files["src/worker.py"] = "def charge():\n    return True\n"
    after = _normalize(full_files=changed_files)

    changed_locators = {
        left.locator for left, right in zip(before, after, strict=True) if left.id != right.id
    }
    assert changed_locators == {"file:src/worker.py:lines:1-2"}


def test_version_change_changes_all_ids() -> None:
    before = _normalize()
    changed_metadata = {**METADATA, "merge_commit_sha": "merge456"}
    after = _normalize(metadata=changed_metadata)

    assert all(left.id != right.id for left, right in zip(before, after, strict=True))


def test_registry_rejects_duplicates_and_unknown_ids() -> None:
    spans = _normalize()
    registry = EvidenceRegistry(spans)

    with pytest.raises(DuplicateEvidenceReference):
        registry.add_all([spans[0]])
    with pytest.raises(UnknownEvidenceReference):
        registry.validate(["missing-evidence"])
    assert registry.get(spans[0].id) == spans[0]


def test_rejects_duplicate_or_unsafe_paths_and_unmatched_full_files() -> None:
    duplicate = [FILES[0], FILES[0]]
    with pytest.raises(ValueError, match="duplicate path"):
        _normalize(files=duplicate)
    with pytest.raises(ValueError, match="unsafe"):
        _normalize(files=[{"filename": "../secret", "status": "modified"}], full_files={})
    with pytest.raises(ValueError, match="no changed-file metadata"):
        _normalize(full_files={**FULL_FILES, "src/other.py": "pass\n"})


def _normalize(
    *,
    metadata: dict | None = None,
    files: list[dict] | None = None,
    full_files: dict[str, str] | None = None,
    observed_at: datetime = OBSERVED_AT,
):
    return normalize_pull_request_evidence(
        PARSED,
        metadata=metadata or METADATA,
        files=files or FILES,
        full_files=full_files if full_files is not None else FULL_FILES,
        observed_at=observed_at,
    )
