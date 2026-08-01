# AGENTS.md — Codex instructions

Codex must read `CLAUDE.md` and treat it as the primary repository instruction file.

## Immediate task

Follow `CODEX_MASTER_PROMPT.md` and complete only Phase 0 and Phase 1 before expanding scope.

## Repository-specific rules

- Mistral APIs are the only allowed model provider.
- Do not create fake connector results in production code. Local demo fixtures must be visibly labelled as demo data.
- Add source citations to every generated claim.
- Keep human approval before all writes.
- Build the alert review experience before a chatbot.
- Prefer a complete vertical slice over broad partial integrations.
- Update `TASKS.md` as work is completed.
- Add an entry to `docs/BUILD_LOG.md` after each meaningful milestone.
