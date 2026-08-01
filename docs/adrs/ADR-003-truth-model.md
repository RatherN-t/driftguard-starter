# ADR-003 — Model evidence, claims, and authority separately

## Status

Accepted.

## Context

“Newest source wins” produces false updates because sources represent implementation, intent, policy, or future plans.

## Decision

Store original evidence, extracted claims, claim relationships, and human-confirmed conclusions as separate layers.

## Consequences

More implementation work, but every conclusion becomes inspectable and reversible.
