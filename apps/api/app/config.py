from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65_535)
    web_origin: str = "http://localhost:3000"
    database_url: str = Field(default="sqlite:///./driftguard.db", min_length=1)
    demo_mode: bool = True

    mistral_api_key: SecretStr | None = None
    mistral_model_fast: str = "mistral-small-latest"
    mistral_model_deep: str = "mistral-medium-latest"
    mistral_transcribe_model: str = "voxtral-mini-latest"
    mistral_text_embed_model: str = "mistral-embed"
    mistral_code_embed_model: str = "codestral-embed"
    audio_max_bytes: int = Field(default=25_000_000, ge=1, le=100_000_000)

    google_service_account_file: str = "./secrets/google-service-account.json"
    google_drive_folder_id: str | None = None
    google_write_enabled: bool = False

    github_token: SecretStr | None = None
    github_max_changed_files: int = Field(default=10, ge=1, le=100)
    github_max_file_bytes: int = Field(default=100_000, ge=1, le=10_000_000)

    email_mode: Literal["console", "smtp"] = "console"

    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65_535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None

    @field_validator("mistral_api_key", "github_token", "smtp_password", mode="before")
    @classmethod
    def empty_secret_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("google_drive_folder_id", mode="before")
    @classmethod
    def empty_optional_string_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


def _secret_is_configured(value: SecretStr | None) -> bool:
    return value is not None and bool(value.get_secret_value().strip())


def configuration_status(settings: Settings) -> dict[str, bool | list[str]]:
    """Return capability readiness without returning configuration values."""
    mistral_configured = _secret_is_configured(settings.mistral_api_key)
    google_credentials_present = Path(settings.google_service_account_file).is_file()
    google_folder_configured = bool(settings.google_drive_folder_id)
    google_read_ready = google_credentials_present and google_folder_configured
    source_read_ready = settings.demo_mode or google_read_ready

    missing_requirements: list[str] = []
    if not mistral_configured:
        missing_requirements.append("MISTRAL_API_KEY")
    if not settings.demo_mode:
        if not google_credentials_present:
            missing_requirements.append("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not google_folder_configured:
            missing_requirements.append("GOOGLE_DRIVE_FOLDER_ID")

    return {
        "boot_ready": True,
        "mode_ready": source_read_ready and mistral_configured,
        "demo_mode": settings.demo_mode,
        "demo_sources_ready": settings.demo_mode,
        "source_read_ready": source_read_ready,
        "analysis_ready": mistral_configured,
        "mistral_configured": mistral_configured,
        "google_read_ready": google_read_ready,
        "google_write_enabled": settings.google_write_enabled,
        "github_authenticated": _secret_is_configured(settings.github_token),
        "smtp_configured": bool(
            settings.smtp_host
            and settings.smtp_username
            and _secret_is_configured(settings.smtp_password)
            and settings.smtp_from
        ),
        "missing_requirements": missing_requirements,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
