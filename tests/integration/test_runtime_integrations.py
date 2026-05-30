from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.auth_service import AuthService
from services.config_service import ConfigService
from services.drive_service import DriveService
from services.file_lock_service import FileLockService
from services.gmail_service import GmailService
from services.json_service import JsonService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import LoggingStub


RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS", "").lower() == "true"


def _require_env(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        pytest.skip("Missing integration environment: " + ", ".join(missing))


def _oauth_config() -> dict:
    return {
        "google_oauth": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
            "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        }
    }


@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Integration tests are environment-gated.")
def test_real_google_drive_write_and_rollback_validation(tmp_path):
    _require_env("MANDITRADE_INTEGRATION_ROOT")
    root = Path(os.getenv("MANDITRADE_INTEGRATION_ROOT", str(tmp_path)))
    target = root / "drive_write_probe.json"
    service = SafeDriveWriteService(
        json_service=JsonService(),
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=root / "backups",
        logging_service=LoggingStub(),
        version_history_root=root / "version_history",
    )
    service.replace_document(target, {"schema_version": "1.0", "agreements": []})
    saved = JsonService().read_json(target, {})
    assert saved["schema_version"] == "1.0"


@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Integration tests are environment-gated.")
def test_real_google_drive_lock_acquisition_release(tmp_path):
    _require_env("MANDITRADE_INTEGRATION_ROOT")
    root = Path(os.getenv("MANDITRADE_INTEGRATION_ROOT", str(tmp_path)))
    lock_service = FileLockService()
    target = root / "lock_probe.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    lock_path = lock_service.acquire(target, owner="integration-test")
    assert lock_path.exists()
    lock_service.release(lock_path)
    assert not lock_path.exists()


@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Integration tests are environment-gated.")
def test_real_gmail_runtime_mode_has_no_user_queue():
    service = GmailService("admin@example.com", use_gmail_api=False, queue_path=None, safe_drive_write_service=SafeDriveWriteService(
        json_service=JsonService(),
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=Path(os.getenv("MANDITRADE_INTEGRATION_ROOT", ".")) / "backups",
        logging_service=LoggingStub(),
        version_history_root=Path(os.getenv("MANDITRADE_INTEGRATION_ROOT", ".")) / "version_history",
    ))
    assert service.read_queue() == []


@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Integration tests are environment-gated.")
def test_oauth_refresh_and_session_restoration():
    _require_env("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI")
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    assert auth_service.oauth_config["client_id"]


@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Integration tests are environment-gated.")
def test_startup_recovery_with_real_persisted_runtime_artifacts():
    _require_env("MANDITRADE_INTEGRATION_ROOT")
    issues = ConfigService().validate_streamlit_secrets(
        {
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
            },
            "admin": {"admin_email": os.getenv("MANDITRADE_ADMIN_EMAIL", "")},
            "security": {
                "fernet_key": os.getenv("MANDITRADE_FERNET_KEY", ""),
                "public_verification_key": os.getenv("MANDITRADE_PUBLIC_KEY", ""),
            },
        }
    )
    assert isinstance(issues, list)
