.PHONY: api web test lint checks models

api:
	uvicorn apps.api.app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

test:
	pytest

lint:
	ruff check apps scripts

checks:
	python scripts/check_mistral_only.py
	python scripts/validate_json_files.py
	pytest

models:
	python scripts/list_mistral_models.py
