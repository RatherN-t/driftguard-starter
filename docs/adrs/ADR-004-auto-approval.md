# ADR-004 — Auto-approve and auto-apply every alert

## Status

Accepted. Supersedes [ADR-002](ADR-002-human-approval.md).

## Context

ADR-002 required a PM or developer to click Approve (or Reject) before DriftGuard would write a
patch, and a separate Apply action before it touched the document. For this workspace that gate
added a step without adding safety: the classification, evidence, and patch are already
source-backed and evidence-cited before a human ever sees them, and the reviewer step was a rubber
stamp in every demo run.

## Decision

Every alert is approved and written back automatically the moment it is first observed (on
`GET /api/alerts`, `GET /api/analysis/current`, or `POST /api/analysis/run`), under a
`system:auto-approval` actor. The `pending_review → approved → applied` state machine and its audit
trail (`ReviewStore`) are unchanged — only who drives the transition changes. The manual
`/approve`, `/reject`, and `/apply` endpoints still exist for live (non-demo) write-back edge cases
where auto-apply can't finish (for example Google write-back disabled), but they are no longer part
of the normal flow and will 409 once an alert is already applied.

The document view highlights exactly what changed: the removed span is struck through in the
"before" column and the replacement span is marked in the "proposed"/"applied" columns, so the
absence of a manual approval step doesn't mean the change is any less visible.

## Consequences

The system can no longer claim a human reviewed every write before it landed — that safeguard is
gone. What remains: every auto-approval and apply is still recorded in the audit trail with an
actor, timestamp, and the exact patch, and the diff is highlighted in place so a human can still
catch a bad change after the fact and correct it in a follow-up run.
