from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.drive_path_resolver import DrivePathResolver
from services.google_drive_service import GoogleDriveService
from services.required_drive_files import build_required_drive_files


class AdminDriveService:
    def __init__(self) -> None:
        self.token_store_path = Path(__file__).resolve().parent.parent / "runtime" / "oauth" / "admin_user_token.json"
        self.google_drive_service = GoogleDriveService(self.token_store_path)

    def _get_drive_config(self) -> dict[str, str]:
        secrets = dict(st.secrets.get("google_drive", {})) if "google_drive" in st.secrets else {}
        return {
            "root_folder_id": str(secrets.get("root_folder_id", "") or "").strip(),
            "root_folder_name": str(secrets.get("root_folder_name", "") or "MANDITRADE_DB").strip(),
        }

    def _get_platform_config(self) -> dict[str, str]:
        secrets = dict(st.secrets.get("platform", {})) if "platform" in st.secrets else {}
        return {
            "primary_admin_email": str(secrets.get("primary_admin_email", "")).strip().lower(),
            "primary_admin_name": str(secrets.get("primary_admin_name", "") or "Primary Admin").strip(),
        }

    def get_required_files_registry(self) -> list[dict]:
        platform = self._get_platform_config()
        return build_required_drive_files(platform["primary_admin_email"], platform["primary_admin_name"])

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

    def get_required_folder_paths(self) -> list[str]:
        folder_paths = {
            "00_config",
            "00_config/languages",
            "01_identity",
            "02_catalog",
            "05_orders",
            "06_shipments",
            "07_ledger",
            "09_notifications",
            "14_runtime",
        }
        return sorted(folder_paths)

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

    def ensure_root_folder(self) -> dict:
        service = self.build_client()
        config = self._get_drive_config()
        root_folder_id = config["root_folder_id"]
        root_folder_name = config["root_folder_name"]
        if root_folder_id:
            root = service.files().get(fileId=root_folder_id, fields="id,name,mimeType").execute()
            return {
                "logical_path": root_folder_name,
                "status": "FOUND",
                "folder_id": root.get("id", ""),
                "file_id": "",
                "actual_path": root.get("name", root_folder_name),
                "error": "",
            }
        root = self.google_drive_service.find_child(service, "root", root_folder_name)
        if root:
            return {
                "logical_path": root_folder_name,
                "status": "FOUND",
                "folder_id": root.get("id", ""),
                "file_id": "",
                "actual_path": root.get("name", root_folder_name),
                "error": "",
            }
        created = self.google_drive_service.find_or_create_folder(service, root_folder_name, None)
        return {
            "logical_path": root_folder_name,
            "status": "CREATED",
            "folder_id": created.get("id", ""),
            "file_id": "",
            "actual_path": created.get("name", root_folder_name),
            "error": "",
        }

    def get_path_resolver(self) -> DrivePathResolver:
        service = self.build_client()
        root = self._resolve_root_folder(service)
        return DrivePathResolver(self.google_drive_service, service, root)

    def clear_runtime_cache(self) -> None:
        st.session_state.pop("mt_next_cache", None)
        st.session_state.pop("mt_next_data", None)

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
            resolver = self.get_path_resolver()
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
        required_folders = []
        missing_folders = []
        for folder_path in self.get_required_folder_paths():
            folder_result = resolver.resolve_folder_path(folder_path)
            required_folders.append(folder_result)
            if folder_result["status"] != "FOUND":
                missing_folders.append(folder_path)
        for item in self.get_required_files_registry():
            result = resolver.resolve_file_path(item["logical_path"])
            required_files.append(result)
            if result["status"] != "FOUND":
                missing_files.append(item["logical_path"])
        return {
            "connected": True,
            "mode": "user_oauth_drive",
            "root_folder_id": resolver.root_folder["id"],
            "root_folder_name": resolver.root_folder["name"],
            "required_folders": required_folders,
            "missing_folders": missing_folders,
            "required_files": required_files,
            "missing_files": missing_files,
            "errors": [],
        }

    def read_json(self, logical_path: str) -> dict:
        resolver = self.get_path_resolver()
        file_result = resolver.resolve_file_path(logical_path)
        if file_result["status"] != "FOUND":
            raise FileNotFoundError(logical_path)
        return self.google_drive_service.read_json_file(resolver.service, file_result["file_id"])

    def write_json(self, logical_path: str, payload: dict) -> dict:
        resolver = self.get_path_resolver()
        return resolver.create_or_update_json_file(logical_path, payload)

    def create_missing_required_files(self) -> dict:
        resolver = self.get_path_resolver()
        created = []
        existing = []
        for item in self.get_required_files_registry():
            logical_path = item["logical_path"]
            result = resolver.resolve_file_path(logical_path)
            if result["status"] == "FOUND":
                existing.append(logical_path)
                if logical_path == "01_identity/users.json":
                    payload = self.read_json(logical_path)
                    users = list(payload.get("users", []))
                    primary_admin = self._get_platform_config()
                    if primary_admin["primary_admin_email"] and not any(str(user.get("email", "")).strip().lower() == primary_admin["primary_admin_email"] for user in users):
                        users.append(
                            {
                                "user_id": f"USR_{len(users) + 1:04d}",
                                "email": primary_admin["primary_admin_email"],
                                "role": "platform_admin",
                                "status": "ACTIVE",
                                "display_name": primary_admin["primary_admin_name"],
                                "source": "toml_primary_admin",
                            }
                        )
                        resolver.create_or_update_json_file(logical_path, {"users": users})
                continue
            created_result = resolver.ensure_json_file(logical_path, item["default_payload"])
            created.append(created_result)
        self.clear_runtime_cache()
        return {"created": created, "existing": existing}

    def create_missing_required_folders(self) -> dict:
        resolver = self.get_path_resolver()
        created = []
        existing = []
        for folder_path in self.get_required_folder_paths():
            result = resolver.resolve_folder_path(folder_path)
            if result["status"] == "FOUND":
                existing.append(folder_path)
                continue
            created.append(resolver.ensure_folder_path(folder_path))
        self.clear_runtime_cache()
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
            manifest = self.get_runtime_manifest()
            scopes = token.get("scopes", [])
            return {
                "connected": True,
                "mode": "user_oauth_drive",
                "source": "session_or_runtime_oauth",
                "root_folder_id": manifest.get("root_folder_id", config["root_folder_id"]),
                "root_folder_name": manifest.get("root_folder_name", config["root_folder_name"]),
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
