# ADR-002 — Require human approval before shared writes

## Status

Superseded by [ADR-004](ADR-004-auto-approval.md). Kept for history: the review/audit state
machine this ADR introduced (`pending_review` → `approved` → `applied`) still exists and is still
recorded, but every alert now advances through it automatically instead of waiting on a human
action.

## Context

Code can differ from documentation because code is wrong, experimental, disabled, or ahead of approved intent.

## Decision

Mistral may propose a canonical statement and patch but may not apply it. A PM or developer must approve.

## Consequences

The system is safer and better aligned with collaborative decision-making. It cannot claim full autonomous maintenance.
