from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.config import get_settings
from apps.api.app.routers import alerts, analysis, demo, evaluations, sources, system

settings = get_settings()
app = FastAPI(title="DriftGuard API", version="0.1.0")

allowed_web_origins = {settings.web_origin}
if settings.app_env == "development":
    allowed_web_origins.update(
        {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_web_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(system.router)
app.include_router(demo.router)
app.include_router(sources.router)
app.include_router(alerts.router)
app.include_router(evaluations.router)
app.include_router(analysis.router)
