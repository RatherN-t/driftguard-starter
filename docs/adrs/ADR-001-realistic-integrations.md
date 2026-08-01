# ADR-001 — Use Google Docs, manual GitHub PR ingestion, and audio upload

## Status

Accepted for hackathon MVP.

## Context

Jira, Confluence, GitHub Apps, webhooks, and Google Meet APIs add authentication and setup risk without proving the core insight.

## Decision

Use:

- one Google Drive folder;
- a pasted GitHub PR URL;
- direct audio/text upload;
- optional SMTP.

## Consequences

The demo is narrower but more reliable. The core evidence architecture remains extensible.
