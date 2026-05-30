from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.ui_shell import render_same_tab_link_button
from services.auth_service import AuthService
from services.connected_accounts_service import ConnectedAccountsService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.oauth_callback_service import OAuthCallbackService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.security_service import SecurityService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import LoggingStub


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
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
        }
    }


def _build_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    security_service = SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=auth_service,
        admin_token_file=tmp_path / "admin_token.enc",
        manufacturer_token_dir=tmp_path / "manufacturer_tokens",
        runtime_tokens_dir=tmp_path / "runtime_tokens",
        require_verification_for_admin_runtime=False,
    )
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    oauth_service = OAuthCallbackService(auth_service, security_service, state_store_path=tmp_path / "oauth_states.json")
    connected_accounts_service = ConnectedAccountsService(
        drive_service=drive,
        security_service=security_service,
        auth_service=auth_service,
        oauth_callback_service=oauth_service,
        json_service=json_service,
        safe_drive_write_service=safe_write,
    )
    drive.initialize_manufacturer_workspace("MANU101", "Shree Agro Traders", owner_email="owner@example.com", city="Pune")
    return auth_service, security_service, oauth_service, connected_accounts_service, drive


def test_same_tab_google_link_button_html():
    html = render_same_tab_link_button("Continue with Google", "https://example.com/auth")
    assert 'target="_blank"' not in html
    assert "target='_self'" in html
    assert "https://example.com/auth" in html


def test_login_scopes_do_not_include_drive_or_gmail(tmp_path):
    st.session_state.clear()
    _auth, _security, oauth_service, _connected, _drive = _build_stack(tmp_path)
    oauth_service.build_authorization_url(flow_type=oauth_service.LOGIN)
    flow_context = st.session_state["oauth_flow_context"]
    assert "https://www.googleapis.com/auth/drive.file" not in flow_context["scopes"]
    assert "https://www.googleapis.com/auth/gmail.send" not in flow_context["scopes"]


def test_manufacturer_drive_connect_scope_uses_drive_file(tmp_path):
    st.session_state.clear()
    _auth, _security, oauth_service, connected_service, _drive = _build_stack(tmp_path)
    connected_service.build_connect_url("MANU101", "drive")
    flow_context = st.session_state["oauth_flow_context"]
    assert flow_context["flow_type"] == oauth_service.MANUFACTURER_DRIVE
    assert flow_context["manufacturer_id"] == "MANU101"
    assert flow_context["scopes"] == ["https://www.googleapis.com/auth/drive.file"]


def test_connected_account_metadata_stays_in_private_zone(tmp_path):
    _auth, _security, _oauth_service, connected_service, drive = _build_stack(tmp_path)
    metadata = connected_service.complete_connection(
        manufacturer_code="MANU101",
        provider="drive",
        credentials_payload={"refresh_token": "refresh-token", "scopes": ["https://www.googleapis.com/auth/drive.file"]},
        connected_email="owner@example.com",
    )
    private_zone = drive.get_manufacturer_paths("MANU101").private_zone
    shared_zone = drive.get_manufacturer_paths("MANU101").shared_zone
    metadata_path = private_zone / "connected_accounts.json"
    token_ref = Path(metadata["drive"]["encrypted_refresh_token_ref"])
    assert metadata_path.exists()
    assert token_ref.exists()
    assert str(metadata_path).startswith(str(private_zone))
    assert str(token_ref).startswith(str(private_zone))
    assert not (shared_zone / "connected_accounts.json").exists()
    assert not any(shared_zone.rglob("*.enc"))
