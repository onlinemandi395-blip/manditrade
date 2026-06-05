from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.google_drive_service import GoogleDriveService


class AdminDriveService:
    def __init__(self) -> None:
        self.token_store_path = Path(__file__).resolve().parent.parent / "runtime" / "oauth" / "admin_user_token.json"
        self.google_drive_service = GoogleDriveService(self.token_store_path)

    def _get_drive_config(self) -> dict[str, str]:
        secrets = dict(st.secrets.get("google_drive", {})) if "google_drive" in st.secrets else {}
        return {
            "root_folder_id": str(secrets.get("root_folder_id", "") or secrets.get("admin_db_root_folder_id", "") or "").strip(),
            "root_folder_name": str(secrets.get("root_folder_name", "") or secrets.get("admin_db_root_folder_name", "") or "MANDITRADE_DB").strip(),
        }

    def _get_user_token(self) -> dict:
        session_user = dict(st.session_state.get("mt_next_user", {}) or {})
        token = dict(session_user.get("oauth_token", {}) or {})
        if token:
            return token
        return self.google_drive_service.read_token_store()

    def build_client(self):
        token = self._get_user_token()
        if not token:
            raise ValueError("Admin OAuth token required.")
        return self.google_drive_service.build_drive_client_from_user_oauth(token)

    def _resolve_root_folder(self, service):
        config = self._get_drive_config()
        root_folder_id = config["root_folder_id"]
        root_folder_name = config["root_folder_name"]
        if root_folder_id:
            try:
                return service.files().get(fileId=root_folder_id, fields="id,name,mimeType").execute()
            except Exception:
                pass
        return self.google_drive_service.find_or_create_folder(service, root_folder_name, None)

    def get_status(self) -> dict:
        config = self._get_drive_config()
        token = self._get_user_token()
        if not token:
            return {
                "connected": False,
                "mode": "user_oauth_drive",
                "source": "missing_admin_token",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "admin_token_available": False,
                "drive_write_test": "FAIL",
                "gmail_send_scope": "missing",
            }
        try:
            service = self.build_client()
            root = self._resolve_root_folder(service)
            scopes = token.get("scopes", [])
            return {
                "connected": True,
                "mode": "user_oauth_drive",
                "source": "session_or_runtime_oauth",
                "root_folder_id": root.get("id", config["root_folder_id"]),
                "root_folder_name": root.get("name", config["root_folder_name"]),
                "admin_token_available": True,
                "drive_write_test": "PASS",
                "gmail_send_scope": "available" if "https://www.googleapis.com/auth/gmail.send" in scopes else "missing",
            }
        except Exception:
            return {
                "connected": False,
                "mode": "user_oauth_drive",
                "source": "session_or_runtime_oauth",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "admin_token_available": True,
                "drive_write_test": "FAIL",
                "gmail_send_scope": "available" if "https://www.googleapis.com/auth/gmail.send" in token.get("scopes", []) else "missing",
            }
