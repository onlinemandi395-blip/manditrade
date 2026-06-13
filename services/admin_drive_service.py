from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from time import time

import streamlit as st

from services.drive_path_resolver import DrivePathResolver
from services.auth_service import is_bootstrap_admin
from services.google_drive_service import GoogleDriveService
from services.performance_service import PerformanceService
from services.required_drive_files import build_required_drive_files


class AdminDriveService:
    VALIDATION_KEY = "drive_validation_result"
    FILE_INDEX_KEY = "drive_file_index"
    ROOT_KEY = "drive_root_metadata"
    VALIDATION_TTL_SECONDS = 300

    def __init__(self) -> None:
        self.token_store_path = Path(__file__).resolve().parent.parent / "runtime" / "oauth" / "admin_user_token.json"
        self.google_drive_service = GoogleDriveService(self.token_store_path)
        self.performance_service = PerformanceService()
        st.session_state.setdefault(self.FILE_INDEX_KEY, {})

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

    def _get_required_file_definition(self, logical_path: str) -> dict | None:
        return next((item for item in self.get_required_files_registry() if item.get("logical_path") == logical_path), None)

    def _get_user_token(self) -> dict:
        stored_token = self.google_drive_service.read_token_store()
        if stored_token:
            return stored_token
        session_user = dict(st.session_state.get("mt_next_user", {}) or {})
        session_email = str(session_user.get("email", "") or "").strip().lower()
        if not is_bootstrap_admin(session_email):
            return {}
        token = dict(session_user.get("oauth_token", {}) or {})
        if token:
            return token
        return {}

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
            "05_orders/marketplace",
            "05_orders/mandiplace",
            "06_shipments",
            "07_ledger",
            "09_notifications",
            "10_audit",
            "14_runtime",
            "15_media",
            "15_media/products",
            "15_media/app_assets",
            "15_media/app_assets/backgrounds",
        }
        return sorted(folder_paths)

    def _resolve_root_folder(self, service):
        cached_root = st.session_state.get(self.ROOT_KEY)
        if cached_root:
            return cached_root
        config = self._get_drive_config()
        root_folder_id = config["root_folder_id"]
        root_folder_name = config["root_folder_name"]
        if root_folder_id:
            try:
                root = service.files().get(fileId=root_folder_id, fields="id,name,mimeType").execute()
                st.session_state[self.ROOT_KEY] = root
                return root
            except Exception as exc:
                raise FileNotFoundError(f"Google Drive root folder not reachable: {root_folder_id}") from exc
        root = self.google_drive_service.find_child(service, "root", root_folder_name)
        if not root:
            raise FileNotFoundError(f"Google Drive root folder not found by name: {root_folder_name}")
        st.session_state[self.ROOT_KEY] = root
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

    def clear_runtime_cache(self, *, clear_validation: bool = True, clear_file_index: bool = False) -> None:
        st.session_state.pop("mt_next_cache", None)
        st.session_state.pop("mt_next_data", None)
        if clear_validation:
            st.session_state.pop(self.VALIDATION_KEY, None)
        if clear_file_index:
            st.session_state[self.FILE_INDEX_KEY] = {}
            st.session_state.pop(self.ROOT_KEY, None)

    def _get_cached_validation(self) -> dict | None:
        cached = st.session_state.get(self.VALIDATION_KEY)
        if not cached:
            return None
        validated_at = float(cached.get("validated_at", 0) or 0)
        if (time() - validated_at) > self.VALIDATION_TTL_SECONDS:
            return None
        return dict(cached)

    def _store_validation(self, manifest: dict) -> dict:
        cached = dict(manifest)
        cached["validated_at"] = time()
        st.session_state[self.VALIDATION_KEY] = cached
        return cached

    def _index_path(self, logical_path: str, file_result: dict) -> None:
        if file_result.get("status") == "FOUND" and file_result.get("file_id"):
            st.session_state[self.FILE_INDEX_KEY][logical_path] = {
                "file_id": file_result.get("file_id", ""),
                "folder_id": file_result.get("folder_id", ""),
                "actual_path": file_result.get("actual_path", ""),
            }

    def _resolve_indexed_file(self, resolver: DrivePathResolver, logical_path: str) -> dict:
        indexed = dict(st.session_state.get(self.FILE_INDEX_KEY, {}).get(logical_path, {}) or {})
        if indexed.get("file_id"):
            return {
                "logical_path": logical_path,
                "status": "FOUND",
                "folder_id": indexed.get("folder_id", ""),
                "file_id": indexed.get("file_id", ""),
                "actual_path": indexed.get("actual_path", logical_path),
                "error": "",
            }
        result = resolver.resolve_file_path(logical_path)
        self._index_path(logical_path, result)
        return result

    def get_runtime_manifest(self, *, force_refresh: bool = False) -> dict:
        if not force_refresh:
            cached = self._get_cached_validation()
            if cached:
                return cached
        config = self._get_drive_config()
        token = self._get_user_token()
        if not token:
            return self._store_validation({
                "connected": False,
                "mode": "admin_user_oauth_drive",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "required_files": [],
                "missing_files": ["Google OAuth admin token"],
                "errors": ["Primary admin OAuth token required for Google Drive runtime."],
            })
        try:
            with self.performance_service.measure("drive_root_resolution"):
                resolver = self.get_path_resolver()
        except Exception as exc:
            return self._store_validation({
                "connected": False,
                "mode": "admin_user_oauth_drive",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "required_files": [],
                "missing_files": [],
                "errors": [str(exc)],
            })
        required_files = []
        missing_files = []
        required_folders = []
        missing_folders = []
        with self.performance_service.measure("required_file_validation"):
            for folder_path in self.get_required_folder_paths():
                folder_result = resolver.resolve_folder_path(folder_path)
                required_folders.append(folder_result)
                if folder_result["status"] != "FOUND":
                    missing_folders.append(folder_path)
            for item in self.get_required_files_registry():
                result = self._resolve_indexed_file(resolver, item["logical_path"])
                required_files.append(result)
                if result["status"] != "FOUND":
                    missing_files.append(item["logical_path"])
        return self._store_validation({
            "connected": True,
            "mode": "admin_user_oauth_drive",
            "root_folder_id": resolver.root_folder["id"],
            "root_folder_name": resolver.root_folder["name"],
            "required_folders": required_folders,
            "missing_folders": missing_folders,
            "required_files": required_files,
            "missing_files": missing_files,
            "errors": [],
        })

    def read_json(self, logical_path: str) -> dict:
        resolver = self.get_path_resolver()
        file_result = self._resolve_indexed_file(resolver, logical_path)
        if file_result["status"] != "FOUND":
            raise FileNotFoundError(logical_path)
        return self.google_drive_service.read_json_file(resolver.service, file_result["file_id"])

    def write_json(self, logical_path: str, payload: dict) -> dict:
        resolver = self.get_path_resolver()
        result = resolver.create_or_update_json_file(logical_path, payload)
        self._index_path(logical_path, result)
        return result

    def get_database_config_status(self) -> dict:
        definition = self._get_required_file_definition("00_config/database.json")
        expected_payload = dict((definition or {}).get("default_payload", {}) or {})
        expected_collections = dict(expected_payload.get("collections", {}) or {})
        try:
            current_payload = self.read_json("00_config/database.json")
        except FileNotFoundError:
            return {
                "logical_path": "00_config/database.json",
                "status": "MISSING",
                "expected_collections": sorted(expected_collections.keys()),
                "current_collection_count": 0,
                "expected_collection_count": len(expected_collections),
                "missing_collections": sorted(expected_collections.keys()),
                "added_collections": [],
            }

        current_collections = dict(current_payload.get("collections", {}) or {})
        missing_collections = sorted(
            name for name in expected_collections.keys() if not str(current_collections.get(name, "")).strip()
        )
        return {
            "logical_path": "00_config/database.json",
            "status": "OK" if not missing_collections else "OUTDATED",
            "expected_collections": sorted(expected_collections.keys()),
            "current_collection_count": len(current_collections),
            "expected_collection_count": len(expected_collections),
            "missing_collections": missing_collections,
            "added_collections": [],
        }

    def migrate_root_orders(self) -> dict:
        root_orders_path = "05_orders/orders.json"
        try:
            root_payload = self.read_json(root_orders_path)
        except FileNotFoundError:
            return {
                "status": "MISSING",
                "root_orders_count": 0,
                "marketplace_added": 0,
                "manditrade_added": 0,
            }

        root_orders = list(root_payload.get("orders", []) or [])
        marketplace_payload = self.read_json("05_orders/marketplace/orders.json")
        manditrade_payload = self.read_json("05_orders/mandiplace/orders.json")
        marketplace_orders = list(marketplace_payload.get("orders", []) or [])
        manditrade_orders = list(manditrade_payload.get("orders", []) or [])
        marketplace_ids = {str(row.get("order_id", "")).strip() for row in marketplace_orders if str(row.get("order_id", "")).strip()}
        manditrade_ids = {str(row.get("order_id", "")).strip() for row in manditrade_orders if str(row.get("order_id", "")).strip()}
        marketplace_added = 0
        manditrade_added = 0

        for order in root_orders:
            source_channel = str(order.get("source_channel", "")).strip().lower()
            order_id = str(order.get("order_id", "")).strip()
            if not order_id:
                continue
            if source_channel == "marketplace":
                if order_id not in marketplace_ids:
                    marketplace_orders.append(order)
                    marketplace_ids.add(order_id)
                    marketplace_added += 1
            elif source_channel in {"manditrade", "mandiplace"}:
                order["source_channel"] = "manditrade"
                if order_id not in manditrade_ids:
                    manditrade_orders.append(order)
                    manditrade_ids.add(order_id)
                    manditrade_added += 1

        self.write_json("05_orders/marketplace/orders.json", {"schema_version": 1, "orders": marketplace_orders})
        self.write_json("05_orders/mandiplace/orders.json", {"schema_version": 1, "orders": manditrade_orders})
        self.clear_runtime_cache(clear_validation=True, clear_file_index=False)
        return {
            "status": "MIGRATED" if (marketplace_added or manditrade_added) else "UNCHANGED",
            "root_orders_count": len(root_orders),
            "marketplace_added": marketplace_added,
            "manditrade_added": manditrade_added,
        }

    def refresh_database_config_mapping(self) -> dict:
        definition = self._get_required_file_definition("00_config/database.json")
        if not definition:
            raise KeyError("Required Drive definition missing for 00_config/database.json")

        logical_path = "00_config/database.json"
        default_payload = deepcopy(dict(definition.get("default_payload", {}) or {}))
        default_collections = dict(default_payload.get("collections", {}) or {})
        try:
            current_payload = self.read_json(logical_path)
            existed = True
        except FileNotFoundError:
            current_payload = {}
            existed = False

        merged_payload = deepcopy(current_payload) if existed else {}
        merged_payload["root"] = str(merged_payload.get("root", "") or default_payload.get("root", "MANDITRADE_DB")).strip() or "MANDITRADE_DB"
        merged_payload["storage_mode"] = (
            str(merged_payload.get("storage_mode", "") or default_payload.get("storage_mode", "google_drive_only")).strip()
            or "google_drive_only"
        )
        current_collections = dict(merged_payload.get("collections", {}) or {})
        added_collections = []
        for collection_name, mapping in default_collections.items():
            if not str(current_collections.get(collection_name, "")).strip():
                current_collections[collection_name] = mapping
                added_collections.append(collection_name)
        merged_payload["collections"] = current_collections

        result = self.write_json(logical_path, merged_payload)
        self.clear_runtime_cache(clear_validation=True, clear_file_index=False)
        return {
            "logical_path": logical_path,
            "status": "CREATED" if not existed else ("UPDATED" if added_collections else "UNCHANGED"),
            "expected_collection_count": len(default_collections),
            "current_collection_count": len(current_collections),
            "added_collections": added_collections,
            "missing_collections": [],
            "file_id": result.get("file_id", ""),
        }

    def create_missing_required_files(self) -> dict:
        resolver = self.get_path_resolver()
        created = []
        existing = []
        updated = []
        for item in self.get_required_files_registry():
            logical_path = item["logical_path"]
            result = resolver.resolve_file_path(logical_path)
            if result["status"] == "FOUND":
                existing.append(logical_path)
                if logical_path == "00_config/database.json":
                    updated.append(self.refresh_database_config_mapping())
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
        self.clear_runtime_cache(clear_validation=True, clear_file_index=False)
        return {"created": created, "existing": existing, "updated": updated}

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
        self.clear_runtime_cache(clear_validation=True, clear_file_index=False)
        return {"created": created, "existing": existing}

    def get_status(self) -> dict:
        config = self._get_drive_config()
        token = self._get_user_token()
        if not token:
            return {
                "connected": False,
                "mode": "admin_user_oauth_drive",
                "source": "missing_primary_admin_token",
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
                "mode": "admin_user_oauth_drive",
                "source": "primary_admin_oauth",
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
                "mode": "admin_user_oauth_drive",
                "source": "primary_admin_oauth",
                "root_folder_id": config["root_folder_id"],
                "root_folder_name": config["root_folder_name"],
                "admin_token_available": True,
                "drive_write_test": "FAIL",
                "gmail_send_scope": "available" if "https://www.googleapis.com/auth/gmail.send" in token.get("scopes", []) else "missing",
                "required_files_status": "missing",
                "missing_files": [],
            }
