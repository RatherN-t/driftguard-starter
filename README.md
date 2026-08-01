# DriftGuard

DriftGuard is a hackathon prototype that detects semantic drift between product documentation, meeting decisions, and implementation changes.

It is built for one concrete cross-disciplinary relationship:

- **Primary user:** a product manager who needs to understand what changed and whether shared documentation is still reliable.
- **Counterpart:** a developer or technical lead who needs the product explanation to stay technically accurate and source-backed.

The core workflow is:

1. Sync product and architecture documents from one Google Drive folder.
2. Paste a GitHub pull-request URL and retrieve the changed files.
3. Optionally upload meeting audio and transcribe it with Mistral Voxtral.
4. Use separate Mistral calls to extract claims, decisions, code changes, and contradictions.
5. Show a product-manager view and a developer view with exact evidence.
6. Propose a minimal Google Docs patch.
7. Auto-approve and write the patch immediately — no human sign-off gate — with every changed
   span highlighted inline in the document view (see [ADR-004](docs/adrs/ADR-004-auto-approval.md)).

## Start here

Read these files in order:

1. `docs/00_START_HERE.md`
2. `CLAUDE.md` or `AGENTS.md`
3. `docs/03_MVP_SCOPE.md`
4. `docs/04_SYSTEM_ARCHITECTURE.md`
5. `docs/13_24H_TEAM_PLAN.md`
6. `TASKS.md`

For Codex, paste the contents of `CODEX_MASTER_PROMPT.md` as the first task.

## Quick setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
uvicorn apps.api.app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

The backend exposes `GET /health`, an evidence-backed demo alert API, source-ingestion routes,
review/audit/write-back endpoints, a transcript decision log, and seeded evaluation results. Demo
mode is credential-free and all fixture data is visibly labelled.

## What the demo actually reads and writes

| Role | Demo source | What happens |
|---|---|---|
| architecture document | `demo/architecture_doc.md` (`demo://architecture_doc.md`) | heading-aware local read; this is the stale shared document |
| repository | `https://github.com/example/driftguard-demo` | identity only; visibly labelled fixture mode does not contact GitHub |
| pull request | `https://github.com/example/driftguard-demo/pull/7` plus `demo/pr_metadata.json` and `demo/code_after/*.py` | local PR metadata and full changed-file evidence |
| meeting | `demo/meeting_transcript.txt` | timestamped speaker evidence and deterministic demo decisions |
| approved output | `uploads/demo_architecture_doc.approved.md` | created automatically as soon as the alignment view is built — auto-approved, no human action needed |

The source setup screen also accepts a Google Docs share URL, matching GitHub repository and PR
URLs, pasted timestamped transcript text, or meeting audio. `POST /api/analysis/run` composes those
sources into one review. `GET /api/analysis/current` returns the exact source IDs and versions plus
the full document before/proposed/applied view.

Before a demo, run:

```bash
python scripts/check_mistral_only.py
python scripts/validate_json_files.py
pytest
python scripts/smoke_test.py
cd apps/web && npm run typecheck && npm run build
```

With both services running, exercise the deployed HTTP workflow:

```bash
python scripts/uat_test.py
```

## Critical eligibility rule

All model inference, transcription, embeddings, OCR, and agentic reasoning must use **Mistral APIs only**. Do not add another model provider, including as a fallback.

## Recommended first milestone

Do not begin with agents, webhooks, or multiple connectors. Make this single vertical slice work first:

> Google Doc claim → GitHub PR change → Mistral drift classification → evidence review → approved Google Docs patch.
