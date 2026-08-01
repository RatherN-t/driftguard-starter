# Start here

## The problem

Modern teams produce more code, documents, tickets, and meeting content than they can keep synchronized. A product manager may read an architecture document that is no longer true because a developer changed the implementation in a pull request. A meeting may approve a change, while the shared document remains stale. The next person then acts on misinformation.

## The product

DriftGuard creates a traceable bridge between product managers and developers. It gathers evidence from a small number of realistic sources, detects semantic drift, explains it at two levels of technical depth, and proposes a reviewable correction.

## One-sentence pitch

> DriftGuard catches when code and team decisions have moved ahead of the documents people still trust, then gives product managers and developers one source-backed explanation and an approved update.

## Hackathon input scope

- One Google Drive folder containing Google Docs.
- One pasted GitHub pull-request URL.
- Optional uploaded meeting audio transcribed by Mistral Voxtral.
- Optional email through console or SMTP.

## Why this is not another summarizer

A summarizer compresses information. DriftGuard performs a harder workflow:

1. extracts claims with provenance;
2. identifies which claims refer to the same system behavior;
3. distinguishes implementation from intent;
4. detects contradictions and supersession;
5. exposes uncertainty;
6. routes a specific human decision;
7. applies a minimal approved correction.

## First build target

Use the included demo fixtures. Make one stale-documentation alert work end to end before connecting real accounts.
