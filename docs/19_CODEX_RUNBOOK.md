# Codex runbook

## First session

Open the repository root in Codex and paste `CODEX_MASTER_PROMPT.md`.

Require Codex to stop after Phase 1. Review the diff and run:

```bash
python scripts/check_mistral_only.py
python scripts/validate_json_files.py
pytest
```

## Subsequent sessions

Give one milestone at a time:

1. Google Docs live read
2. GitHub full-file context
3. structured Mistral extraction
4. drift review UI
5. approval and write-back
6. Voxtral decisions
7. email and evaluation

For each session, require:

- files changed;
- tests added;
- commands run;
- known limitations;
- no unrelated refactors.

## Prompt template

```text
Read CLAUDE.md, TASKS.md, and the relevant numbered design document.
Implement only task: <TASK>.
Follow the existing interfaces and schemas.
Add tests for success and failure paths.
Do not add another model provider.
Do not broaden scope.
Run checks and update TASKS.md and docs/BUILD_LOG.md.
Stop after reporting the diff and test results.
```

## Review checkpoints

Do not accept a Codex change when:

- claims lack evidence IDs;
- a write can happen without approval;
- code is treated as automatically canonical;
- a model output is parsed from arbitrary prose;
- a connector has no timeout/error handling;
- demo fixtures are passed off as live data;
- another model SDK appears in dependencies.
