import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import (
    AnalysisRunResult,
    AuditEvent,
    DocumentPatchProposal,
    DriftAlert,
    FeedbackRecord,
)


class InvalidReviewTransition(ValueError):
    pass


class ReviewStore:
    def __init__(self, database_url: str):
        path = _sqlite_path(database_url)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._initialize()

    def ensure_alert(self, alert: DriftAlert) -> str:
        with self.lock, self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO review_states
                    (alert_id, status, proposal_json, evidence_json, updated_at)
                VALUES (?, 'pending_review', ?, ?, ?)
                """,
                (
                    alert.id,
                    alert.patch.model_dump_json(),
                    json.dumps(alert.classification.evidence_ids),
                    datetime.now(UTC).isoformat(),
                ),
            )
            row = self.connection.execute(
                "SELECT status FROM review_states WHERE alert_id = ?", (alert.id,)
            ).fetchone()
        return str(row["status"])

    def transition(
        self,
        alert: DriftAlert,
        *,
        action: str,
        actor_id: str,
        comment: str | None = None,
        reason_code: str | None = None,
    ) -> AuditEvent:
        if action not in {"approve", "reject"}:
            raise ValueError("Unsupported review action")
        new_state = "approved" if action == "approve" else "rejected"
        event_type = "alert_approved" if action == "approve" else "alert_rejected"
        now = datetime.now(UTC)
        with self.lock, self.connection:
            self.ensure_alert(alert)
            row = self.connection.execute(
                "SELECT status, proposal_json, evidence_json FROM review_states WHERE alert_id = ?",
                (alert.id,),
            ).fetchone()
            prior_state = str(row["status"])
            if prior_state != "pending_review":
                raise InvalidReviewTransition(
                    f"Cannot {action} an alert in {prior_state} state"
                )
            event_id = f"audit:{uuid.uuid4()}"
            self.connection.execute(
                "UPDATE review_states SET status = ?, updated_at = ? WHERE alert_id = ?",
                (new_state, now.isoformat(), alert.id),
            )
            self.connection.execute(
                """
                INSERT INTO review_audit
                    (id, alert_id, actor_id, event_type, prior_state, new_state,
                     proposal_json, evidence_json, comment, reason_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    alert.id,
                    actor_id,
                    event_type,
                    prior_state,
                    new_state,
                    row["proposal_json"],
                    row["evidence_json"],
                    comment,
                    reason_code,
                    now.isoformat(),
                ),
            )
        return AuditEvent(
            id=event_id,
            alert_id=alert.id,
            actor_id=actor_id,
            event_type=event_type,
            prior_state=prior_state,
            new_state=new_state,
            proposed_patch=alert.patch,
            evidence_ids=alert.classification.evidence_ids,
            comment=comment,
            reason_code=reason_code,
            created_at=now,
        )

    def list_audit(self, alert_id: str) -> list[AuditEvent]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM review_audit WHERE alert_id = ? ORDER BY created_at, id",
                (alert_id,),
            ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                alert_id=row["alert_id"],
                actor_id=row["actor_id"],
                event_type=row["event_type"],
                prior_state=row["prior_state"],
                new_state=row["new_state"],
                proposed_patch=DocumentPatchProposal.model_validate_json(row["proposal_json"]),
                evidence_ids=json.loads(row["evidence_json"]),
                comment=row["comment"],
                reason_code=row["reason_code"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def current_status(self, alert: DriftAlert) -> str:
        return self.ensure_alert(alert)

    def mark_applied(self, alert: DriftAlert, *, actor_id: str) -> AuditEvent:
        now = datetime.now(UTC)
        with self.lock, self.connection:
            self.ensure_alert(alert)
            row = self.connection.execute(
                "SELECT status, proposal_json, evidence_json FROM review_states WHERE alert_id = ?",
                (alert.id,),
            ).fetchone()
            prior_state = str(row["status"])
            if prior_state != "approved":
                raise InvalidReviewTransition(
                    f"Cannot apply an alert in {prior_state} state"
                )
            event_id = f"audit:{uuid.uuid4()}"
            self.connection.execute(
                "UPDATE review_states SET status = 'applied', updated_at = ? WHERE alert_id = ?",
                (now.isoformat(), alert.id),
            )
            self.connection.execute(
                """
                INSERT INTO review_audit
                    (id, alert_id, actor_id, event_type, prior_state, new_state,
                     proposal_json, evidence_json, comment, reason_code, created_at)
                VALUES (?, ?, ?, 'patch_applied', 'approved', 'applied', ?, ?, NULL, NULL, ?)
                """,
                (
                    event_id,
                    alert.id,
                    actor_id,
                    row["proposal_json"],
                    row["evidence_json"],
                    now.isoformat(),
                ),
            )
        return AuditEvent(
            id=event_id,
            alert_id=alert.id,
            actor_id=actor_id,
            event_type="patch_applied",
            prior_state="approved",
            new_state="applied",
            proposed_patch=alert.patch,
            evidence_ids=alert.classification.evidence_ids,
            created_at=now,
        )

    def reset(self) -> None:
        with self.lock, self.connection:
            self.connection.execute("DELETE FROM active_analysis")
            self.connection.execute("DELETE FROM review_feedback")
            self.connection.execute("DELETE FROM notification_log")
            self.connection.execute("DELETE FROM review_audit")
            self.connection.execute("DELETE FROM review_states")

    def save_active_analysis(self, result: AnalysisRunResult) -> None:
        with self.lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO active_analysis (slot, result_json, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(slot) DO UPDATE SET
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (result.model_dump_json(), datetime.now(UTC).isoformat()),
            )

    def load_active_analysis(self) -> AnalysisRunResult | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT result_json FROM active_analysis WHERE slot = 1"
            ).fetchone()
        if row is None:
            return None
        return AnalysisRunResult.model_validate_json(row["result_json"])

    def clear_active_analysis(self) -> None:
        with self.lock, self.connection:
            self.connection.execute("DELETE FROM active_analysis")

    def record_notification(
        self, alert_id: str, deduplication_key: str, *, actor_id: str
    ) -> bool:
        with self.lock, self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO notification_log
                    (alert_id, deduplication_key, actor_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (alert_id, deduplication_key, actor_id, datetime.now(UTC).isoformat()),
            )
        return cursor.rowcount == 1

    def remove_notification(self, alert_id: str, deduplication_key: str) -> None:
        """Release a failed delivery reservation so a human can retry safely."""
        with self.lock, self.connection:
            self.connection.execute(
                """
                DELETE FROM notification_log
                WHERE alert_id = ? AND deduplication_key = ?
                """,
                (alert_id, deduplication_key),
            )

    def record_feedback(
        self,
        alert: DriftAlert,
        *,
        actor_id: str,
        verdict: str,
        comment: str | None,
    ) -> FeedbackRecord:
        self.ensure_alert(alert)
        now = datetime.now(UTC)
        feedback_id = f"feedback:{uuid.uuid4()}"
        evidence_ids = alert.classification.evidence_ids
        with self.lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO review_feedback
                    (id, alert_id, actor_id, verdict, comment, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    alert.id,
                    actor_id,
                    verdict,
                    comment,
                    json.dumps(evidence_ids),
                    now.isoformat(),
                ),
            )
        return FeedbackRecord(
            id=feedback_id,
            alert_id=alert.id,
            actor_id=actor_id,
            verdict=verdict,
            comment=comment,
            evidence_ids=evidence_ids,
            created_at=now,
        )

    def list_feedback(self, alert_id: str) -> list[FeedbackRecord]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM review_feedback WHERE alert_id = ? ORDER BY created_at, id",
                (alert_id,),
            ).fetchall()
        return [
            FeedbackRecord(
                id=row["id"],
                alert_id=row["alert_id"],
                actor_id=row["actor_id"],
                verdict=row["verdict"],
                comment=row["comment"],
                evidence_ids=json.loads(row["evidence_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def _initialize(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_states (
                    alert_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_audit (
                    id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    prior_state TEXT NOT NULL,
                    new_state TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    comment TEXT,
                    reason_code TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notification_log (
                    alert_id TEXT NOT NULL,
                    deduplication_key TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (alert_id, deduplication_key)
                );
                CREATE TABLE IF NOT EXISTS review_feedback (
                    id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    comment TEXT,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS active_analysis (
                    slot INTEGER PRIMARY KEY CHECK (slot = 1),
                    result_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            notification_columns = {
                str(row[1])
                for row in self.connection.execute(
                    "PRAGMA table_info(notification_log)"
                ).fetchall()
            }
            if "actor_id" not in notification_columns:
                self.connection.execute(
                    """
                    ALTER TABLE notification_log
                    ADD COLUMN actor_id TEXT NOT NULL DEFAULT 'system:legacy'
                    """
                )


@lru_cache
def get_review_store() -> ReviewStore:
    return ReviewStore(get_settings().database_url)


def _sqlite_path(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported for the MVP")
    path = database_url.removeprefix(prefix)
    if not path:
        raise ValueError("SQLite database path must not be empty")
    return path
