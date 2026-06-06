from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.google_drive_service import GoogleDriveService


class AdminDriveService:
    REQUIRED_RUNTIME_FILES = [
        "00_config/app_config.json",
        "00_config/auth.json",
        "00_config/permissions.json",
        "00_config/role_views.json",
        "00_config/navigation.json",
        "00_config/modules.json",
        "00_config/dashboards.json",
        "00_config/forms.json",
        "00_config/database.json",
        "00_config/languages/en.json",
        "00_config/languages/hi.json",
        "00_config/languages/mr.json",
        "00_config/languages/bn.json",
        "01_identity/users.json",
        "02_catalog/product_mapping.json",
        "02_catalog/raw_materials.json",
        "05_orders/orders.json",
        "06_shipments/shipments.json",
        "07_ledger/ledger.json",
        "09_notifications/notifications.json",
        "09_notifications/gmail_queue.json",
    ]

    def __init__(self) -> None:
        self.token_store_path = Path(__file__).resolve().parent.parent / "runtime" / "oauth" / "admin_user_token.json"
        self.google_drive_service = GoogleDriveService(self.token_store_path)

    def _get_drive_config(self) -> dict[str, str]:
        secrets = dict(st.secrets.get("google_drive", {})) if "google_drive" in st.secrets else {}
        return {
            "root_folder_id": str(secrets.get("root_folder_id", "") or "").strip(),
            "root_folder_name": str(secrets.get("root_folder_name", "") or "MANDITRADE_DB").strip(),
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
            except Exception as exc:
                raise FileNotFoundError(f"Google Drive root folder not reachable: {root_folder_id}") from exc
        root = self.google_drive_service.find_child(service, "root", root_folder_name)
        if not root:
            raise FileNotFoundError(f"Google Drive root folder not found by name: {root_folder_name}")
        return root

    def get_runtime_manifest(self) -> dict:
        config = self._get_drive_config()
        token = self._get_user_token()
        if not token:
            return {
                "connected": False,
                "mode": "user_oauth_drive",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "required_files": [],
                "missing_files": ["Google OAuth admin token"],
                "errors": ["Admin OAuth token required for Google Drive runtime."],
            }
        try:
            service = self.build_client()
            root = self._resolve_root_folder(service)
        except Exception as exc:
            return {
                "connected": False,
                "mode": "user_oauth_drive",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "required_files": [],
                "missing_files": [],
                "errors": [str(exc)],
            }

        required_files = []
        missing_files = []
        for logical_path in self.REQUIRED_RUNTIME_FILES:
            metadata = self.google_drive_service.resolve_logical_path(service, root["id"], logical_path)
            row = {
                "logical_path": logical_path,
                "exists": bool(metadata),
                "drive_file_id": (metadata or {}).get("id", ""),
                "type": "folder" if (metadata or {}).get("mimeType") == "application/vnd.google-apps.folder" else "file",
                "last_modified": (metadata or {}).get("modifiedTime", ""),
            }
            required_files.append(row)
            if not metadata:
                missing_files.append(logical_path)
        return {
            "connected": True,
            "mode": "user_oauth_drive",
            "root_folder_id": root["id"],
            "root_folder_name": root["name"],
            "required_files": required_files,
            "missing_files": missing_files,
            "errors": [],
        }

    def read_json(self, logical_path: str) -> dict:
        service = self.build_client()
        root = self._resolve_root_folder(service)
        return self.google_drive_service.read_json_by_path(service, root["id"], logical_path)

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
                "required_files_status": "missing",
                "missing_files": ["Google OAuth admin token"],
            }
        try:
            service = self.build_client()
            root = self._resolve_root_folder(service)
            scopes = token.get("scopes", [])
            manifest = self.get_runtime_manifest()
            return {
                "connected": True,
                "mode": "user_oauth_drive",
                "source": "session_or_runtime_oauth",
                "root_folder_id": root.get("id", config["root_folder_id"]),
                "root_folder_name": root.get("name", config["root_folder_name"]),
                "admin_token_available": True,
                "drive_write_test": "PASS",
                "gmail_send_scope": "available" if "https://www.googleapis.com/auth/gmail.send" in scopes else "missing",
                "required_files_status": "ok" if not manifest["missing_files"] else "missing",
                "missing_files": manifest["missing_files"],
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
                "required_files_status": "missing",
                "missing_files": [],
            }
