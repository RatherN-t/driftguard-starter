# Codex master prompt

You are building DriftGuard from this repository. Read `CLAUDE.md`, `docs/00_START_HERE.md`, `docs/03_MVP_SCOPE.md`, `docs/04_SYSTEM_ARCHITECTURE.md`, and `TASKS.md` before editing files.

## Goal

Implement a working vertical slice in which:

1. The app imports one architecture document from Google Docs or the local demo fixture.
2. The user pastes one GitHub PR URL or loads the local demo PR fixture.
3. Mistral extracts a documented claim and an implementation claim using strict Pydantic structured outputs.
4. Mistral classifies the implementation as making the document stale.
5. The frontend shows the current claim, new evidence, PM explanation, developer explanation, and proposed minimal patch.
6. The user approves the patch.
7. In real integration mode, the app updates Google Docs using revision control. In demo mode, it updates a local copy while clearly labelling the result.
8. An audit event is stored.

## Required implementation sequence

### Phase 0

- Make the backend and frontend boot.
- Implement configuration validation.
- Add `/health` and `/api/config/status` without exposing secrets.
- Load demo fixtures.
- Run tests.

### Phase 1

- Implement document chunking and evidence IDs.
- Implement GitHub URL parsing and read-only API client.
- Implement the Mistral gateway using `client.chat.parse` and schemas.
- Implement the deterministic evidence-ID validator.
- Implement the drift pipeline against demo fixtures.
- Expose one alert through the API.
- Render the review page.

Stop after Phase 1 and provide:

- changed files;
- commands run;
- test results;
- remaining blockers;
- the exact next task.

## Do not do yet

- OAuth
- webhooks
- Jira or Confluence
- Slack
- Mistral Workflows
- Mistral Agents or handoffs
- embeddings
- audio transcription
- email delivery
- production deployment

These are later milestones. The first vertical slice must be stable before adding them.
