# Demo and pitch plan

## Five-minute MVP demo

### 0:00–0:35 — problem

“AI makes it cheap to create code and documents, but expensive to know which one is still true. Product managers make decisions from architecture docs that quietly fell behind the implementation.”

### 0:35–0:55 — user

Introduce one product manager and one developer. State the current manual workflow and failure.

### 0:55–1:15 — product

“DriftGuard connects the evidence they already create, detects semantic drift, and produces one reviewable shared explanation.”

### 1:15–3:50 — live demo

1. Click **Load perfect demo** and show the exact document, repository, PR, and transcript links.
2. Point out that fixture mode reads `demo/architecture_doc.md`, `demo/pr_metadata.json`, and the two full changed Python files without contacting GitHub or Google.
3. Show the stale-documentation alert and open the synchronous document evidence versus queue, worker, HTTP 202, and pending-state code evidence.
4. Toggle Product and Developer views; point out confidence and the unresolved customer failure message.
5. Show the full document before and proposed-after panes, then the transcript decision log with Priya's timestamped approval.
6. Enter the reviewer name and approve the minimal patch; explain that approval alone did not write anything.
7. Click **Apply to demo copy** and show the third **Actually written** document pane plus the audit state.
8. Close on the seeded evaluation: 8/8 exact cases, full citation coverage, and zero hard-negative false positives.

### 3:50–4:30 — technical depth

Show the pipeline diagram and emphasize:

- separate Mistral stages;
- structured outputs and unknown-evidence rejection;
- Voxtral transcription and Mistral/Codestral retrieval;
- revision-safe, approval-gated writes;
- hard-negative evaluation.

### 4:30–4:50 — trust and feasibility

Explain why code is not automatically truth, why citations are mandatory, and why approval and application are separate actions.

### 4:50–5:00 — close

“DriftGuard does not help teams create more information. It helps them stop acting on information that is no longer true.”

## Backup demo

- Keep the app and fixtures local.
- Run `python scripts/smoke_test.py` immediately before judging.
- Use the local demo-copy write and email preview; do not depend on external credentials.
- Keep a screen recording or screenshots only if the team has created them.
- Ensure demo reset takes one click.
