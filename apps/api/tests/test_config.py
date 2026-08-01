from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.app.config import Settings, configuration_status, get_settings
from apps.api.app.main import app


def test_example_environment_contains_no_sample_secrets() -> None:
    example = (Path(__file__).resolve().parents[3] / ".env.example").read_text(encoding="utf-8")

    for variable in ("MISTRAL_API_KEY", "GITHUB_TOKEN", "SMTP_PASSWORD"):
        assert f"{variable}=" in example.splitlines()


def test_demo_mode_boots_without_external_credentials() -> None:
    settings = Settings(
        _env_file=None,
        demo_mode=True,
        mistral_api_key=None,
        github_token=None,
        google_drive_folder_id=None,
        google_service_account_file="missing-service-account.json",
    )

    status = configuration_status(settings)

    assert status["boot_ready"] is True
    assert status["demo_sources_ready"] is True
    assert status["source_read_ready"] is True
    assert status["analysis_ready"] is False
    assert status["mode_ready"] is False
    assert status["missing_requirements"] == ["MISTRAL_API_KEY"]


def test_live_mode_reports_missing_requirements_without_values() -> None:
    settings = Settings(
        _env_file=None,
        demo_mode=False,
        mistral_api_key=None,
        github_token=None,
        google_drive_folder_id=None,
        google_service_account_file="missing-service-account.json",
    )

    status = configuration_status(settings)

    assert status["boot_ready"] is True
    assert status["source_read_ready"] is False
    assert status["mode_ready"] is False
    assert status["missing_requirements"] == [
        "MISTRAL_API_KEY",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_DRIVE_FOLDER_ID",
    ]


def test_live_mode_is_ready_with_required_configuration(tmp_path: Path) -> None:
    service_account_file = tmp_path / "service-account.json"
    service_account_file.write_text("{}", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        demo_mode=False,
        mistral_api_key="configured-mistral-secret",
        google_drive_folder_id="configured-folder",
        google_service_account_file=str(service_account_file),
    )

    status = configuration_status(settings)

    assert status["mode_ready"] is True
    assert status["analysis_ready"] is True
    assert status["google_read_ready"] is True
    assert status["missing_requirements"] == []


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_port=0)


def test_config_endpoint_never_exposes_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    mistral_secret = "mistral-secret-that-must-not-appear"
    github_secret = "github-secret-that-must-not-appear"
    monkeypatch.setenv("MISTRAL_API_KEY", mistral_secret)
    monkeypatch.setenv("GITHUB_TOKEN", github_secret)
    get_settings.cache_clear()

    try:
        response = TestClient(app).get("/api/config/status")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["mistral_configured"] is True
    assert response.json()["github_authenticated"] is True
    assert mistral_secret not in response.text
    assert github_secret not in response.text
    assert "api_key" not in response.text.lower()
    assert "token" not in response.text.lower()
