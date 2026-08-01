# Deployment runbook

## Local demo — safest

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Configuration

1. Copy `.env.example` to `.env`.
2. Add `MISTRAL_API_KEY`.
3. Put Google credentials under `secrets/` and configure the path.
4. Add Drive folder ID.
5. Add optional GitHub token.
6. Keep email in console mode until SMTP works.

## Pre-demo smoke test

```bash
python scripts/check_mistral_only.py
python scripts/validate_json_files.py
pytest
python scripts/smoke_test.py
cd apps/web && npm run typecheck && npm run build
```

Manual checks:

- Mistral API works;
- demo reset works;
- Google folder is shared;
- GitHub PR is accessible;
- document update uses a test copy;
- email preview renders;
- browser tabs are pre-opened;
- backup recording is available.

## Production-shaped deployment

For a hosted demo:

- deploy frontend and API together if time is limited;
- use SQLite only on a persistent volume or switch to managed PostgreSQL;
- store secrets in platform secret configuration;
- set CORS explicitly;
- enforce upload size limits;
- disable debug mode.

## Rollback

The audit log stores before text. If a Google Docs update is wrong, the demo UI should present the original text and a manual restore operation. Do not build automatic rollback before the main write path is stable.
