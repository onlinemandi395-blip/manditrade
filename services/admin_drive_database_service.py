from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
    ) -> None:
        self.drive_path_service = drive_path_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.runtime_root = runtime_root
        self.system_config = system_config
        self.secret_overrides = secret_overrides or {}

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
        return {
            "root_folder_id": root_id,
            "root_folder_name": root_name,
            "source": source,
            "root_path": str(self.drive_path_service.db_root),
            "admin_drive_db_enabled": bool(storage_cfg.get("admin_drive_db_enabled", True)),
        }

    def ensure_database_root(self, *, allow_create: bool = True) -> dict[str, Any]:
        config = self.resolve_root_config()
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
        if allow_create:
            self.drive_path_service.ensure_canonical_structure()
        checks = []
        for folder in self.drive_path_service.FOLDER_TREE.values():
            target = self.drive_path_service.db_root / folder
            checks.append({"path": str(target), "exists": target.exists()})
        return {"folders": checks, "all_present": all(item["exists"] for item in checks)}

    def ensure_required_json_files(self, *, allow_create: bool = True) -> dict[str, Any]:
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
