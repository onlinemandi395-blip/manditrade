from __future__ import annotations

import json
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
        "00_config/categories.json",
        "00_config/database.json",
        "00_config/languages/en.json",
        "00_config/languages/hi.json",
        "00_config/languages/mr.json",
        "00_config/languages/bn.json",
        "01_identity/users.json",
        "02_catalog/products.json",
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

    def write_json(self, logical_path: str, payload: dict) -> dict:
        service = self.build_client()
        root = self._resolve_root_folder(service)
        parent_path, file_name = logical_path.rsplit("/", 1)
        parent = root
        for part in [item for item in parent_path.split("/") if item]:
            parent = self.google_drive_service.find_or_create_folder(service, part, parent["id"])
        return self.google_drive_service.create_or_update_json_file(service, parent["id"], file_name, payload)

    def create_missing_required_files(self) -> dict:
        base_dir = Path(__file__).resolve().parent.parent
        templates = {
            "00_config/app_config.json": base_dir / "configs" / "app_config.json",
            "00_config/auth.json": base_dir / "configs" / "auth.json",
            "00_config/permissions.json": base_dir / "configs" / "permissions.json",
            "00_config/role_views.json": base_dir / "configs" / "role_views.json",
            "00_config/navigation.json": base_dir / "configs" / "navigation.json",
            "00_config/modules.json": base_dir / "configs" / "modules.json",
            "00_config/dashboards.json": base_dir / "configs" / "dashboards.json",
            "00_config/forms.json": base_dir / "configs" / "forms.json",
            "00_config/database.json": base_dir / "configs" / "database.json",
            "00_config/categories.json": base_dir / "configs" / "categories.json",
            "00_config/languages/en.json": base_dir / "configs" / "languages" / "en.json",
            "00_config/languages/hi.json": base_dir / "configs" / "languages" / "hi.json",
            "00_config/languages/mr.json": base_dir / "configs" / "languages" / "mr.json",
            "00_config/languages/bn.json": base_dir / "configs" / "languages" / "bn.json",
            "01_identity/users.json": base_dir / "configs" / "users.json",
            "02_catalog/products.json": base_dir / "configs" / "products.json",
            "05_orders/orders.json": None,
            "06_shipments/shipments.json": None,
            "07_ledger/ledger.json": None,
            "09_notifications/notifications.json": None,
            "09_notifications/gmail_queue.json": None,
        }
        created = []
        existing = []
        for logical_path in self.REQUIRED_RUNTIME_FILES:
            try:
                existing_payload = self.read_json(logical_path)
                if existing_payload is not None:
                    existing.append(logical_path)
                    continue
            except Exception:
                pass
            template_path = templates.get(logical_path)
            if template_path and template_path.exists():
                payload = json.loads(template_path.read_text(encoding="utf-8"))
            else:
                top_key = Path(logical_path).stem
                payload = {"schema_version": 1, top_key: []}
            self.write_json(logical_path, payload)
            created.append(logical_path)
        return {"created": created, "existing": existing}

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
