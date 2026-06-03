from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaInMemoryUpload


class AdminDriveDatabaseService:
    INVALID_CANONICAL_MESSAGE = "Canonical storage mode requested, but validated Admin Drive DB report is missing."

    def __init__(
        self,
        *,
        drive_path_service,
        safe_drive_write_service,
        json_service,
        runtime_root: Path,
        system_config: dict[str, Any],
        secret_overrides: dict[str, Any] | None = None,
        drive_service=None,
        security_service=None,
        auth_service=None,
        logging_service=None,
    ) -> None:
        self.drive_path_service = drive_path_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.runtime_root = runtime_root
        self.system_config = system_config
        self.secret_overrides = secret_overrides or {}
        self.drive_service = drive_service
        self.security_service = security_service
        self.auth_service = auth_service
        self.logging_service = logging_service

    @property
    def reports_dir(self) -> Path:
        target = self.runtime_root / "release_reports"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def resolve_root_config(self) -> dict[str, Any]:
        storage_cfg = self.system_config.setdefault("storage", {})
        google_secret = dict(self.secret_overrides.get("google_drive", {}) or {})
        root_id = str(
            google_secret.get("admin_db_root_folder_id")
            or storage_cfg.get("admin_db_root_folder_id")
            or ""
        ).strip()
        root_name = str(
            google_secret.get("admin_db_root_folder_name")
            or storage_cfg.get("admin_db_root_folder_name")
            or self.drive_path_service.ROOT_FOLDER_NAME
        ).strip() or self.drive_path_service.ROOT_FOLDER_NAME
        source = "local_fallback"
        if google_secret.get("admin_db_root_folder_id") or google_secret.get("admin_db_root_folder_name"):
            source = "streamlit_secrets"
        elif storage_cfg.get("admin_db_root_folder_id") or storage_cfg.get("admin_db_root_folder_name"):
            source = "system_config"
        runtime_status = self.runtime_status()
        return {
            "root_folder_id": root_id,
            "root_folder_name": root_name,
            "source": source,
            "root_path": str(self.drive_path_service.db_root),
            "admin_drive_db_enabled": bool(storage_cfg.get("admin_drive_db_enabled", True)),
            "runtime_backend": runtime_status["runtime_backend"],
            "drive_api_requested": runtime_status["drive_api_requested"],
            "drive_api_ready": runtime_status["drive_api_ready"],
            "runtime_reason": runtime_status["reason"],
        }

    def ensure_database_root(self, *, allow_create: bool = True) -> dict[str, Any]:
        config = self.resolve_root_config()
        if self._should_use_drive_api():
            return self._ensure_drive_database_root(config, allow_create=allow_create)
        root = self.drive_path_service.db_root
        existed = root.exists()
        if allow_create:
            self.drive_path_service.ensure_root()
        reachable = root.exists()
        return {
            **config,
            "exists": reachable,
            "created": bool(not existed and reachable and allow_create),
        }

    def ensure_folder_tree(self, *, allow_create: bool = True) -> dict[str, Any]:
        if self._should_use_drive_api():
            return self._ensure_drive_folder_tree(allow_create=allow_create)
        if allow_create:
            self.drive_path_service.ensure_canonical_structure()
        checks = []
        for folder in self.drive_path_service.FOLDER_TREE.values():
            target = self.drive_path_service.db_root / folder
            checks.append({"path": str(target), "exists": target.exists()})
        return {"folders": checks, "all_present": all(item["exists"] for item in checks)}

    def ensure_required_json_files(self, *, allow_create: bool = True) -> dict[str, Any]:
        if self._should_use_drive_api():
            return self._ensure_drive_required_json_files(allow_create=allow_create)
        created: list[str] = []
        existing: list[str] = []
        missing: list[str] = []
        for path, payload in self.drive_path_service.bootstrap_file_definitions().items():
            if path.exists():
                existing.append(str(path))
                continue
            if allow_create:
                self.safe_drive_write_service.replace_document(path, payload)
                created.append(str(path))
            else:
                missing.append(str(path))
        return {"created": created, "existing": existing, "missing": missing}

    def get_file_id(self, logical_path: str, *, year_month: str | None = None) -> str:
        return self.get_or_create_json_file(logical_path, year_month=year_month)["file_id"]

    def get_or_create_json_file(
        self,
        logical_path: str,
        default_payload: dict[str, Any] | None = None,
        *,
        year_month: str | None = None,
        allow_create: bool = True,
    ) -> dict[str, Any]:
        target = self.drive_path_service.path(logical_path, year_month=year_month)
        if not target.exists() and allow_create:
            payload = default_payload or {"schema_version": 1, "records": [], "updated_at": ""}
            self.safe_drive_write_service.replace_document(target, payload)
        return {
            "logical_path": logical_path,
            "file_id": target.as_posix(),
            "path": str(target),
            "exists": target.exists(),
        }

    def validate_database_tree(self, *, persist: bool = True) -> dict[str, Any]:
        root = self.ensure_database_root(allow_create=False)
        tree = self.ensure_folder_tree(allow_create=False)
        bootstrap = self.ensure_required_json_files(allow_create=False)
        errors: list[str] = []
        warnings: list[str] = []
        runtime_status = self.runtime_status()
        if runtime_status["drive_api_requested"] and not runtime_status["drive_api_ready"]:
            warnings.append(runtime_status["reason"])
        if not root["exists"]:
            errors.append("Configured admin DB root is not reachable.")
        if not tree["all_present"]:
            errors.append("Canonical Admin Drive folder tree is incomplete.")
        if bootstrap["missing"]:
            warnings.append(f"Missing bootstrap JSON files: {len(bootstrap['missing'])}")
        required_media = [
            self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["media"] / "products",
            self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["media"] / "raw_materials",
            self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["media"] / "payment_proofs",
        ]
        media_ok = all(path.exists() for path in required_media)
        if not media_ok:
            errors.append("Required media folders are missing.")
        sample_partition = self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["orders"] / "marketplace" / self.drive_path_service.current_year_month() / "marketplace_orders.json"
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "PASS" if not errors else "FAIL",
            "runtime": runtime_status,
            "root": root,
            "folder_tree": tree,
            "bootstrap_files": bootstrap,
            "media_ok": media_ok,
            "month_partition_sample": str(sample_partition),
            "errors": errors,
            "warnings": warnings,
            "critical_errors": len(errors),
        }
        if persist:
            self._write_report(report, prefix="admin_drive_db_validation", latest_name="latest_admin_drive_db_validation.json")
        return report

    def bootstrap(self, *, dry_run: bool) -> dict[str, Any]:
        root = self.ensure_database_root(allow_create=not dry_run)
        tree = self.ensure_folder_tree(allow_create=not dry_run)
        bootstrap = self.ensure_required_json_files(allow_create=not dry_run)
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "mode": "dry_run" if dry_run else "execute",
            "runtime": self.runtime_status(),
            "root": root,
            "folder_tree": tree,
            "bootstrap_files": bootstrap,
            "recommendation": "PASS" if root["exists"] and tree["all_present"] and not bootstrap["missing"] else "REVIEW",
        }
        self._write_report(
            report,
            prefix="admin_drive_db_bootstrap",
            latest_name=f"latest_admin_drive_db_bootstrap_{'dry_run' if dry_run else 'execute'}.json",
        )
        return report

    def load_latest_validation_report(self) -> dict[str, Any]:
        return self._read_report(self.reports_dir / "latest_admin_drive_db_validation.json")

    def load_latest_bootstrap_report(self, *, dry_run: bool | None = None) -> dict[str, Any]:
        if dry_run is None:
            candidates = sorted(self.reports_dir.glob("latest_admin_drive_db_bootstrap_*.json"))
            for path in reversed(candidates):
                report = self._read_report(path)
                if report:
                    return report
            return {}
        return self._read_report(self.reports_dir / f"latest_admin_drive_db_bootstrap_{'dry_run' if dry_run else 'execute'}.json")

    def canonical_mode_blockers(self) -> list[str]:
        if not self.system_config.get("storage", {}).get("admin_drive_db_enabled", True):
            return []
        validation = self.load_latest_validation_report()
        if validation and validation.get("status") == "PASS" and not validation.get("critical_errors"):
            return []
        return [self.INVALID_CANONICAL_MESSAGE]

    def generate_structure_report(self) -> dict[str, Any]:
        root = self.resolve_root_config()
        tree = self.ensure_folder_tree(allow_create=False)
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "runtime": self.runtime_status(),
            "root": root,
            "folders": tree["folders"],
            "bootstrap_files": sorted(str(path) for path in self.drive_path_service.bootstrap_file_definitions()),
        }
        self._write_report(report, prefix="admin_drive_db_structure", latest_name="latest_admin_drive_db_structure.json")
        return report

    def _write_report(self, report: dict[str, Any], *, prefix: str, latest_name: str) -> None:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target = self.reports_dir / f"{prefix}_{timestamp}.json"
        latest = self.reports_dir / latest_name
        self.safe_drive_write_service.replace_document(target, report)
        self.safe_drive_write_service.replace_document(latest, report)

    def _read_report(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return self.json_service.read_json(path, {})

    def runtime_status(self) -> dict[str, Any]:
        drive_api_requested = bool(self.drive_service and getattr(self.drive_service, "use_drive_api", False))
        if not drive_api_requested:
            return {
                "runtime_backend": "local_path_mirror",
                "drive_api_requested": False,
                "drive_api_ready": False,
                "reason": "Drive API storage runtime is disabled.",
            }
        try:
            self._build_admin_drive_client()
            return {
                "runtime_backend": "google_drive_api",
                "drive_api_requested": True,
                "drive_api_ready": True,
                "reason": "",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "runtime_backend": "local_path_mirror",
                "drive_api_requested": True,
                "drive_api_ready": False,
                "reason": str(exc),
            }

    def _should_use_drive_api(self) -> bool:
        status = self.runtime_status()
        return bool(status["drive_api_requested"] and status["drive_api_ready"])

    def _build_admin_drive_client(self):
        if not self.drive_service or not self.auth_service or not self.security_service:
            raise RuntimeError("Admin Drive DB runtime hooks are not fully configured.")
        if not getattr(self.drive_service, "use_drive_api", False):
            raise RuntimeError("Drive API storage runtime is disabled.")
        if not self.security_service.admin_token_ready():
            raise RuntimeError("Admin runtime token is not provisioned for Admin Drive DB.")
        refresh_token = self.security_service.decrypt_refresh_token(self.security_service.admin_token_file)
        credentials_payload = self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
        credentials = self.auth_service.refresh_credentials(credentials_payload)
        return self.drive_service.build_drive_client(credentials)

    def _ensure_drive_database_root(self, config: dict[str, Any], *, allow_create: bool) -> dict[str, Any]:
        result = dict(config)
        result.update({"exists": False, "created": False, "error": ""})
        try:
            client = self._build_admin_drive_client()
            folder = None
            if config.get("root_folder_id"):
                try:
                    payload = client.files().get(fileId=config["root_folder_id"], fields="id,name,mimeType,trashed").execute()
                    if payload.get("mimeType") == "application/vnd.google-apps.folder" and not payload.get("trashed", False):
                        folder = payload
                except Exception:
                    folder = None
            if folder is None:
                folder = self._find_drive_item(
                    client,
                    name=config["root_folder_name"],
                    parent_id=None,
                    mime_type="application/vnd.google-apps.folder",
                )
            if folder is None and allow_create:
                folder = client.files().create(
                    body={"name": config["root_folder_name"], "mimeType": "application/vnd.google-apps.folder"},
                    fields="id,name,mimeType",
                ).execute()
                result["created"] = True
            if folder:
                result["exists"] = True
                result["root_folder_id"] = folder.get("id", result.get("root_folder_id", ""))
                result["root_folder_name"] = folder.get("name", result.get("root_folder_name", ""))
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)
            if self.logging_service:
                self.logging_service.log_error("drive_failures", "Admin Drive DB root resolution failed", result)
        return result

    def _ensure_drive_folder_tree(self, *, allow_create: bool) -> dict[str, Any]:
        root = self.ensure_database_root(allow_create=allow_create)
        checks: list[dict[str, Any]] = []
        if not root.get("exists"):
            return {"folders": checks, "all_present": False}
        client = self._build_admin_drive_client()
        root_id = root["root_folder_id"]
        all_present = True
        for folder in self.drive_path_service.canonical_relative_folders():
            created = False
            current_parent = root_id
            folder_id = ""
            for part in folder.parts:
                existing = self._find_drive_item(
                    client,
                    name=part,
                    parent_id=current_parent,
                    mime_type="application/vnd.google-apps.folder",
                )
                if existing is None and allow_create:
                    existing = client.files().create(
                        body={
                            "name": part,
                            "mimeType": "application/vnd.google-apps.folder",
                            "parents": [current_parent],
                        },
                        fields="id,name,mimeType,parents",
                    ).execute()
                    created = True
                if existing is None:
                    all_present = False
                    folder_id = ""
                    current_parent = ""
                    break
                folder_id = existing.get("id", "")
                current_parent = folder_id
            checks.append(
                {
                    "path": str(folder).replace("\\", "/"),
                    "exists": bool(folder_id),
                    "folder_id": folder_id,
                    "created": created,
                }
            )
        return {"folders": checks, "all_present": all_present and all(item["exists"] for item in checks)}

    def _ensure_drive_required_json_files(self, *, allow_create: bool) -> dict[str, Any]:
        root = self.ensure_database_root(allow_create=allow_create)
        created: list[str] = []
        existing: list[str] = []
        missing: list[str] = []
        if not root.get("exists"):
            return {"created": created, "existing": existing, "missing": missing}
        self._ensure_drive_folder_tree(allow_create=allow_create)
        client = self._build_admin_drive_client()
        root_id = root["root_folder_id"]
        for path, payload in self.drive_path_service.bootstrap_file_definitions().items():
            relative = path.relative_to(self.drive_path_service.db_root)
            folder_id = self._resolve_drive_folder_chain(client, root_id, relative.parts[:-1], allow_create=allow_create)
            display_path = relative.as_posix()
            if not folder_id:
                missing.append(display_path)
                continue
            existing_file = self._find_drive_item(client, name=relative.name, parent_id=folder_id, mime_type=None)
            if existing_file:
                existing.append(display_path)
                continue
            if not allow_create:
                missing.append(display_path)
                continue
            media = MediaInMemoryUpload(json.dumps(payload).encode("utf-8"), mimetype="application/json", resumable=False)
            client.files().create(
                body={"name": relative.name, "parents": [folder_id]},
                media_body=media,
                fields="id,name,parents",
            ).execute()
            created.append(display_path)
        return {"created": created, "existing": existing, "missing": missing}

    def _resolve_drive_folder_chain(self, client, root_id: str, parts: tuple[str, ...], *, allow_create: bool) -> str:
        current_parent = root_id
        for part in parts:
            existing = self._find_drive_item(
                client,
                name=part,
                parent_id=current_parent,
                mime_type="application/vnd.google-apps.folder",
            )
            if existing is None and allow_create:
                existing = client.files().create(
                    body={
                        "name": part,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [current_parent],
                    },
                    fields="id,name,parents",
                ).execute()
            if existing is None:
                return ""
            current_parent = existing.get("id", "")
        return current_parent

    def _find_drive_item(self, client, *, name: str, parent_id: str | None, mime_type: str | None):
        escaped_name = str(name).replace("'", "\\'")
        query_parts = ["trashed=false", f"name='{escaped_name}'"]
        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")
        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")
        response = client.files().list(
            q=" and ".join(query_parts),
            pageSize=10,
            fields="files(id,name,mimeType,parents)",
        ).execute()
        files = response.get("files", [])
        return files[0] if files else None
