from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from services.auth_service import AuthService
from services.config_service import ConfigService
from services.encryption_service import EncryptionService
from services.google_runtime_diagnostic_service import GoogleRuntimeDiagnosticService
from services.oauth_callback_service import OAuthCallbackService
from services.security_service import SecurityService


def _oauth_config() -> dict:
    return {
        "google_oauth": {
            "client_id": "client-id",
            "client_secret": "client-secret",
            "redirect_uri": "https://example.streamlit.app",
            "project_id": "project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        }
    }


def _build_security_service(tmp_path: Path, auth_service: AuthService) -> SecurityService:
    return SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=auth_service,
        admin_token_file=tmp_path / "admin_token.enc",
        manufacturer_token_dir=tmp_path / "manufacturer_tokens",
        runtime_tokens_dir=tmp_path / "runtime_tokens",
        require_verification_for_admin_runtime=False,
    )


def test_create_authenticated_user_succeeds_when_mock_auth_disabled():
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    user = auth_service.create_authenticated_user(
        profile={"email": "admin@example.com", "name": "Admin User", "id": "google-subject-123", "verified_email": True},
        email="admin@example.com",
        role="admin",
        subject_id="google-subject-123",
        granted_scopes=["openid"],
        token_metadata={"refresh_token_present": True},
    )
    assert user.email == "admin@example.com"
    assert user.role == "admin"
    assert user.session_source == "google_oauth"
    assert user.subject_id == "google-subject-123"


def test_oauth_callback_session_initialization_succeeds_with_mock_auth_disabled(tmp_path):
    st.session_state.clear()
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    security_service = _build_security_service(tmp_path, auth_service)
    callback_service = OAuthCallbackService(auth_service, security_service, state_store_path=tmp_path / "oauth_states.json")

    callback_service.initialize_session(
        user_payload={
            "email": "manufacturer@example.com",
            "name": "Manufacturer User",
            "role": "manufacturer",
            "subject_id": "subject-456",
            "granted_scopes": ["openid"],
            "profile": {
                "email": "manufacturer@example.com",
                "name": "Manufacturer User",
                "id": "subject-456",
                "verified_email": True,
            },
        },
        credentials_payload={
            "refresh_token": "refresh-token",
            "scopes": ["openid"],
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "redirect_uri": "https://example.streamlit.app",
        },
        manufacturer_code="MANU101",
        session_source="google_oauth",
    )

    assert st.session_state["user"]["session_source"] == "google_oauth"
    assert st.session_state["auth_tokens"]["session_source"] == "google_oauth"
    assert st.session_state["auth_tokens"]["subject_id"] == "subject-456"
    assert Path(st.session_state["auth_tokens"]["token_file"]).exists()


def test_mock_auth_is_rejected_in_staging_cloud_profile():
    system_config = {
        "app": {"runtime_environment": "staging_cloud", "demo_mode": False},
        "notifications": {"notification_mode": "live"},
        "security": {"enable_mock_auth": True},
    }
    oauth_config = {"google_oauth": {"redirect_uri": "https://example.streamlit.app"}}
    result = ConfigService().validate_deployment_profile(system_config, oauth_config)
    assert "staging_cloud runtime cannot expose mock authentication." in result["blockers"]


def test_mock_auth_is_rejected_in_production_profile():
    system_config = {
        "app": {"runtime_environment": "production", "demo_mode": False},
        "notifications": {"notification_mode": "live"},
        "security": {"enable_mock_auth": True},
    }
    oauth_config = {"google_oauth": {"redirect_uri": "https://example.streamlit.app"}}
    result = ConfigService().validate_deployment_profile(system_config, oauth_config)
    assert "production runtime cannot expose mock authentication." in result["blockers"]


def test_localhost_mock_auth_still_allowed():
    auth_service = AuthService(_oauth_config(), enable_mock_auth=True)
    user = auth_service.create_mock_user("admin@manditrade.local", "Local Admin", "admin")
    assert user.session_source == "mock"
    assert user.email == "admin@manditrade.local"


def test_oauth_status_reports_runtime_and_session_source(tmp_path, monkeypatch):
    st.session_state.clear()
    st.session_state["runtime_environment"] = "staging_cloud"
    st.session_state["auth_tokens"] = {"session_source": "google_oauth", "granted_scopes": ["openid"]}
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    security_service = _build_security_service(tmp_path, auth_service)

    class FakeCredentials:
        token = "token"
        refresh_token = "refresh"
        scopes = ["openid"]

    diagnostic_service = GoogleRuntimeDiagnosticService(
        auth_service=auth_service,
        security_service=security_service,
        drive_service=SimpleNamespace(),
        gmail_service=SimpleNamespace(),
        runtime_reports_root=tmp_path / "reports",
    )
    monkeypatch.setattr(diagnostic_service, "get_current_credentials", lambda _user: FakeCredentials())
    user = auth_service.create_authenticated_user(
        profile={"email": "admin@example.com", "name": "Admin", "id": "sub-1", "verified_email": True},
        email="admin@example.com",
        role="admin",
        subject_id="sub-1",
        granted_scopes=["openid"],
    )
    status = diagnostic_service.oauth_status(user)
    assert status["runtime_environment"] == "staging_cloud"
    assert status["mock_auth_enabled"] is False
    assert status["session_source"] == "google_oauth"
    assert status["granted_scopes"] == ["openid"]


def test_admin_vault_is_initialized_once_and_allows_future_unlocks(tmp_path, monkeypatch):
    st.session_state.clear()
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    security_service = SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=auth_service,
        admin_token_file=tmp_path / "admin_token.enc",
        manufacturer_token_dir=tmp_path / "manufacturer_tokens",
        runtime_tokens_dir=tmp_path / "runtime_tokens",
        require_verification_for_admin_runtime=True,
    )

    monkeypatch.setattr(security_service, "get_admin_email", lambda: "admin@example.com")
    monkeypatch.setattr(security_service, "get_public_verification_key", lambda: "verify-123")
    monkeypatch.setattr(security_service, "admin_token_ready", lambda: True)
    monkeypatch.setattr(security_service, "decrypt_refresh_token", lambda *_args, **_kwargs: "refresh-token")
    monkeypatch.setattr(
        security_service,
        "build_runtime_credentials_payload",
        lambda refresh_token, **_kwargs: {
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )

    class FakeCredentials:
        token = "token"

    monkeypatch.setattr(auth_service, "refresh_credentials", lambda _payload: FakeCredentials())
    user = auth_service.create_authenticated_user(
        profile={"email": "admin@example.com", "name": "Admin", "id": "sub-1", "verified_email": True},
        email="admin@example.com",
        role="platform_admin",
        subject_id="sub-1",
        granted_scopes=["openid"],
    )

    first = security_service.unlock_admin_runtime(user, "verify-123")
    assert first["vault_enabled"] is True
    assert security_service.admin_vault_ready() is True

    second = security_service.unlock_admin_runtime(user, "")
    assert second["vault_enabled"] is True
