import threading
from functools import lru_cache

from apps.api.app.domain.schemas import AnalysisRunResult
from apps.api.app.services.review_store import ReviewStore, get_review_store


class ActiveAnalysisStore:
    def __init__(self, persistence: ReviewStore | None = None) -> None:
        self._result: AnalysisRunResult | None = None
        self._persistence = persistence
        self._lock = threading.RLock()

    def _store(self) -> ReviewStore:
        return self._persistence or get_review_store()

    def get(self) -> AnalysisRunResult | None:
        with self._lock:
            if self._result is None:
                self._result = self._store().load_active_analysis()
            return self._result

    def set(self, result: AnalysisRunResult) -> None:
        with self._lock:
            self._result = result
            self._store().save_active_analysis(result)

    def clear(self) -> None:
        with self._lock:
            self._result = None
            self._store().clear_active_analysis()


@lru_cache
def get_active_analysis_store() -> ActiveAnalysisStore:
    return ActiveAnalysisStore()
