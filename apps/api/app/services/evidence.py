from collections.abc import Iterable

from apps.api.app.domain.schemas import EvidenceSpan


class UnknownEvidenceReference(ValueError):
    pass


class DuplicateEvidenceReference(ValueError):
    pass


class EvidenceRegistry:
    def __init__(self, evidence: Iterable[EvidenceSpan] = ()) -> None:
        self._evidence: dict[str, EvidenceSpan] = {}
        self.add_all(evidence)

    def add_all(self, evidence: Iterable[EvidenceSpan]) -> None:
        pending = list(evidence)
        ids = [item.id for item in pending]
        duplicates = {item_id for item_id in ids if ids.count(item_id) > 1}
        duplicates.update(item_id for item_id in ids if item_id in self._evidence)
        if duplicates:
            raise DuplicateEvidenceReference(f"Duplicate evidence IDs: {sorted(duplicates)}")
        self._evidence.update((item.id, item) for item in pending)

    def validate(self, referenced_ids: Iterable[str]) -> None:
        validate_evidence_references(self._evidence.values(), referenced_ids)

    def all(self) -> list[EvidenceSpan]:
        return list(self._evidence.values())

    def get(self, evidence_id: str) -> EvidenceSpan:
        try:
            return self._evidence[evidence_id]
        except KeyError as exc:
            raise UnknownEvidenceReference(f"Unknown evidence ID: {evidence_id}") from exc


def validate_evidence_references(evidence: Iterable[EvidenceSpan], referenced_ids: Iterable[str]) -> None:
    provided = {item.id for item in evidence}
    unknown = set(referenced_ids) - provided
    if unknown:
        raise UnknownEvidenceReference(f"Unknown evidence IDs: {sorted(unknown)}")
