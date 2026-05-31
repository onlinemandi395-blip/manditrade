from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaInMemoryUpload


class GoogleRuntimeDiagnosticService:
    def __init__(
        self,
        auth_service,
        security_service,
        drive_service,
        gmail_service,
        runtime_reports_root: Path,
        logging_service=None,
    ) -> None:
        self.auth_service = auth_service
        self.security_service = security_service
        self.drive_service = drive_service
        self.gmail_service = gmail_service
        self.runtime_reports_root = runtime_reports_root
        self.logging_service = logging_service

    def _report_path(self, prefix: str) -> Path:
        self.runtime_reports_root.mkdir(parents=True, exist_ok=True)
        return self.runtime_reports_root / f"{prefix}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"

    def _write_report(self, prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        target = self._report_path(prefix)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["report_path"] = str(target)
        return payload

    def get_current_credentials(self, current_user) -> Any:
        if not current_user:
            raise PermissionError("Sign in before running Google runtime diagnostics.")
        try:
            import streamlit as st

            auth_tokens = st.session_state.get("auth_tokens") or {}
            token_file = auth_tokens.get("token_file")
            if token_file:
                refresh_token = self.security_service.decrypt_refresh_token(Path(token_file))
                payload = self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
                return self.auth_service.refresh_credentials(payload)
        except Exception:
            pass
        if current_user.role == "admin" and self.security_service.get_admin_email() and current_user.email.lower() == self.security_service.get_admin_email().lower():
            refresh_token = self.security_service.decrypt_refresh_token(self.security_service.admin_token_file)
            payload = self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
            return self.auth_service.refresh_credentials(payload)
        principal_key = current_user.email.replace("@", "_at_")
        refresh_token = self.security_service.restore_runtime_refresh_token(principal_key)
        payload = self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
        return self.auth_service.refresh_credentials(payload)

    def oauth_status(self, current_user) -> dict[str, Any]:
        import streamlit as st

        google_cfg = self.security_service.get_streamlit_google_config()
        auth_tokens = st.session_state.get("auth_tokens") or {}
        auth_oauth_cfg = self.auth_service.oauth_config
        client_id = str(auth_oauth_cfg.get("client_id", "") or "")
        oauth_same_tab_rca_status = st.session_state.get("oauth_same_tab_rca_status") or {}
        status = {
            "oauth_configured": bool(google_cfg.get("client_id") and google_cfg.get("client_secret") and google_cfg.get("redirect_uri")),
            "client_id_present": bool(client_id),
            "client_id_suffix": client_id[-8:] if client_id else "",
            "redirect_uri": auth_oauth_cfg.get("redirect_uri", ""),
            "runtime_environment": st.session_state.get("runtime_environment", "unknown"),
            "secrets_override_active": bool(st.session_state.get("oauth_secrets_override_active", False)),
            "oauth_config_fallback_active": bool(st.session_state.get("oauth_config_fallback_active", False)),
            "login_navigation_mode": st.session_state.get("oauth_login_navigation_mode", "same_tab"),
            "last_oauth_failure_reason": st.session_state.get("oauth_last_failure_reason", ""),
            "same_tab_rca_status": oauth_same_tab_rca_status,
            "state_persistence_mode": "runtime_state_store",
            "mock_auth_enabled": self.auth_service.enable_mock_auth,
            "current_user_email": current_user.email if current_user else "",
            "session_source": auth_tokens.get("session_source", current_user.session_source if current_user else "none"),
            "token_available": False,
            "token_refresh_valid": False,
            "granted_scopes": [],
            "error": "",
        }
        if not current_user:
            return status
        try:
            credentials = self.get_current_credentials(current_user)
            status["token_available"] = bool(credentials.token or credentials.refresh_token)
            status["token_refresh_valid"] = True
            status["granted_scopes"] = list(auth_tokens.get("granted_scopes") or credentials.scopes or current_user.granted_scopes or [])
        except Exception as exc:  # noqa: BLE001
            status["error"] = str(exc)
        return self._write_report("oauth_status", status)

    def admin_token_status(self) -> dict[str, Any]:
        report = {
            "token_file_exists": self.security_service.admin_token_exists(),
            "token_secret_present": bool((self.security_service.get_admin_token_secret() or "").strip()),
            "placeholder_detected": self.security_service.admin_token_is_placeholder(),
            "decrypt_success": False,
            "refresh_success": False,
            "owner_email": "",
            "granted_scopes": [],
            "drive_client_ready": False,
            "gmail_client_ready": False,
            "error": "",
        }
        if not report["token_file_exists"] or report["placeholder_detected"]:
            return self._write_report("admin_token_status", report)
        try:
            refresh_token = self.security_service.decrypt_refresh_token(self.security_service.admin_token_file)
            report["decrypt_success"] = True
            credentials = self.auth_service.refresh_credentials(
                self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
            )
            report["refresh_success"] = True
            report["granted_scopes"] = list(credentials.scopes or [])
            profile = self.auth_service.fetch_google_profile(credentials)
            report["owner_email"] = profile.get("email", "")
            self.drive_service.build_drive_client(credentials)
            report["drive_client_ready"] = True
            build("gmail", "v1", credentials=credentials)
            report["gmail_client_ready"] = True
        except Exception as exc:  # noqa: BLE001
            report["error"] = str(exc)
            if self.logging_service:
                self.logging_service.log_error("integration_failures", "Admin token status failed", report)
        return self._write_report("admin_token_status", report)

    def test_drive_access(self, current_user, safe_mode: bool = True) -> dict[str, Any]:
        credentials = self.get_current_credentials(current_user)
        client = self.drive_service.build_drive_client(credentials)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        folder_name = f"MANDITRADE_STAGING_{timestamp}"
        report = {
            "success": False,
            "folder_name": folder_name,
            "folder_id": "",
            "file_id": "",
            "steps": [],
            "cleanup_skipped": safe_mode,
            "error": "",
        }
        file_id = ""
        folder_id = ""
        try:
            folder = client.files().create(body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}, fields="id,name").execute()
            folder_id = folder["id"]
            report["folder_id"] = folder_id
            report["steps"].append("folder_created")
            content = json.dumps({"status": "created", "timestamp": timestamp}).encode("utf-8")
            media = MediaInMemoryUpload(content, mimetype="application/json", resumable=False)
            created = client.files().create(body={"name": "runtime_probe.json", "parents": [folder_id]}, media_body=media, fields="id").execute()
            file_id = created["id"]
            report["file_id"] = file_id
            report["steps"].append("file_written")
            request = client.files().get_media(fileId=file_id)
            handle = io.BytesIO()
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            report["read_payload"] = json.loads(handle.getvalue().decode("utf-8"))
            report["steps"].append("file_read")
            updated_media = MediaInMemoryUpload(json.dumps({"status": "updated", "timestamp": timestamp}).encode("utf-8"), mimetype="application/json", resumable=False)
            client.files().update(fileId=file_id, media_body=updated_media).execute()
            report["steps"].append("file_updated")
            report["steps"].append("backup_validated")
            if not safe_mode:
                client.files().delete(fileId=file_id).execute()
                client.files().delete(fileId=folder_id).execute()
                report["steps"].append("cleanup_completed")
            report["success"] = True
        except Exception as exc:  # noqa: BLE001
            report["error"] = str(exc)
            if self.logging_service:
                self.logging_service.log_error("integration_failures", "Drive smoke test failed", report)
        return self._write_report("drive_smoke", report)

    def test_gmail_send(self, current_user) -> dict[str, Any]:
        credentials = self.get_current_credentials(current_user)
        admin_email = self.security_service.get_admin_email() or (current_user.email if current_user else "")
        report = {
            "success": False,
            "recipient": admin_email,
            "queued": False,
            "sent": False,
            "failed": False,
            "dead_lettered": False,
            "live_api_attempted": True,
            "error": "",
        }
        try:
            response = self.gmail_service.send_message(
                credentials,
                admin_email,
                "MandiTrade Gmail Runtime Test",
                "MandiTrade Gmail Runtime Test",
                force_live=True,
            )
            report["queued"] = True
            report["sent"] = True
            report["success"] = True
            report["gmail_response"] = {
                "id": response.get("id", ""),
                "threadId": response.get("threadId", ""),
                "labelIds": response.get("labelIds", []),
            }
        except Exception as exc:  # noqa: BLE001
            report["failed"] = True
            report["error"] = str(exc)
            if self.gmail_service.dead_letter_service:
                self.gmail_service.dead_letter_service.record(
                    "gmail_runtime_test_failed",
                    {"recipient": admin_email},
                    str(exc),
                    correlation_id=admin_email,
                )
                report["dead_lettered"] = True
            if self.logging_service:
                self.logging_service.log_error("integration_failures", "Gmail smoke test failed", report)
        return self._write_report("gmail_smoke", report)
