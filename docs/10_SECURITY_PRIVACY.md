# Security and privacy

## Threats

- prompt injection hidden inside documents or code;
- accidental leakage of private repository content;
- over-broad Google or GitHub credentials;
- unauthorized document writes;
- stale patch overwriting a recent human edit;
- duplicate email or update after retries;
- model hallucination presented as fact.

## Controls

### Credentials

- server-side only;
- excluded from Git;
- least-privilege access;
- read-only GitHub token;
- Google editor permission only when write-back is tested;
- no secrets in logs or model prompts.

### Prompt injection

- mark source content as untrusted evidence;
- use strict system prompts;
- do not expose write tools during evidence analysis;
- allowlist model functions;
- reject tool instructions found inside source content.

### Provenance

- every claim references valid evidence IDs;
- source versions and hashes are stored;
- unknown evidence references fail validation;
- uncertainty is visible.

### Writes

- require user approval;
- use optimistic concurrency/revision control;
- validate target text before mutation;
- make operations idempotent;
- store before and after text.

### Email

- send links and summaries by default, not proprietary source code;
- deduplicate notifications;
- use console preview if SMTP is not configured.

## Privacy story for judges

The demo processes a deliberately small project scope. A production version would add OAuth, tenant isolation, configurable retention, regional inference, deletion controls, audit export, and enterprise policy integration. The hackathon architecture does not require rebuilding the evidence model to add these controls.
