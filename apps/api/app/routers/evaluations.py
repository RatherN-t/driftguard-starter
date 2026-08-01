from fastapi import APIRouter

from apps.api.app.config import get_settings
from apps.api.app.domain.schemas import EvaluationReport
from apps.api.app.services.evaluation import run_gold_evaluation

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.get("/gold", response_model=EvaluationReport)
def gold_evaluation() -> EvaluationReport:
    return run_gold_evaluation(get_settings())
