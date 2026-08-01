from fastapi import APIRouter

from apps.api.app.config import configuration_status, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "driftguard-api"}


@router.get("/api/config/status")
def config_status() -> dict:
    return configuration_status(get_settings())
