from pathlib import Path

from apps.api.app.config import Settings
from apps.api.app.services.active_analysis import ActiveAnalysisStore
from apps.api.app.services.analysis_pipeline import build_default_analysis
from apps.api.app.services.review_store import ReviewStore


def test_active_analysis_survives_store_recreation(tmp_path: Path) -> None:
    persistence = ReviewStore(f"sqlite:///{tmp_path / 'active.db'}")
    result = build_default_analysis(
        Settings(_env_file=None, demo_mode=True, mistral_api_key=None)
    )

    ActiveAnalysisStore(persistence).set(result)
    restored = ActiveAnalysisStore(persistence).get()

    assert restored == result

    ActiveAnalysisStore(persistence).clear()
    assert ActiveAnalysisStore(persistence).get() is None
    persistence.connection.close()
