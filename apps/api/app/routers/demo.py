import json
from pathlib import Path

from fastapi import APIRouter

from apps.api.app.services.active_analysis import get_active_analysis_store
from apps.api.app.services.review_store import get_review_store
from apps.api.app.services.writeback import reset_demo_copy

router = APIRouter(prefix="/api/demo", tags=["demo"])
ROOT = Path(__file__).resolve().parents[4]


@router.post("/load")
def load_demo() -> dict:
    demo = ROOT / "demo"
    return {
        "provenance": {
            "mode": "demo_fixture",
            "is_demo": True,
            "label": "DEMO DATA - local fixtures, not live connector results",
        },
        "architecture_document": (demo / "architecture_doc.md").read_text(encoding="utf-8"),
        "product_requirements": (demo / "product_requirements.md").read_text(encoding="utf-8"),
        "meeting_transcript": (demo / "meeting_transcript.txt").read_text(encoding="utf-8"),
        "pr": json.loads((demo / "pr_metadata.json").read_text(encoding="utf-8")),
        "expected_alert": json.loads((demo / "expected_alert.json").read_text(encoding="utf-8")),
    }


@router.post("/reset")
def reset_demo() -> dict:
    get_active_analysis_store().clear()
    get_review_store().reset()
    reset_demo_copy()
    return {
        "status": "reset",
        "provenance": {
            "mode": "demo_fixture",
            "is_demo": True,
            "label": "DEMO DATA - local review state reset",
        },
    }
