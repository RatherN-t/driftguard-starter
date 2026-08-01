import pytest

from apps.api.app.config import get_settings
from apps.api.app.services.active_analysis import get_active_analysis_store
from apps.api.app.services.review_store import get_review_store


@pytest.fixture(autouse=True)
def isolate_external_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """Ensure the test suite never calls configured live providers or prints secrets."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'isolated.db'}")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("MISTRAL_API_KEY", "")
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/test-not-configured.json")
    monkeypatch.setenv("GOOGLE_WRITE_ENABLED", "false")
    monkeypatch.setenv("EMAIL_MODE", "console")
    get_settings.cache_clear()
    get_review_store.cache_clear()
    get_active_analysis_store().clear()
    yield
    get_active_analysis_store().clear()
    get_review_store.cache_clear()
    get_settings.cache_clear()
