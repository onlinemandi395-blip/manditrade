from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CanonicalStorageValidationService:
    REQUIRED_DIRS = [
        "registry",
        "catalog",
        "orders",
        "notifications",
        "analytics",
        "runtime",
        "media",
    ]
    CRITICAL_DIRS = {"registry", "catalog"}

    def __init__(
        self,
        *,
        drive_path_service,
        json_service,
        governance_root: Path,
        public_buyers_root: Path,
        runtime_root: Path,
        safe_drive_write_service,
    ) -> None:
        self.drive_path_service = drive_path_service
        self.json_service = json_service
        self.governance_root = governance_root
        self.public_buyers_root = public_buyers_root
        self.runtime_root = runtime_root
        self.safe_drive_write_service = safe_drive_write_service

    def validate(self, *, rehearsal: bool = False, persist: bool = True) -> dict[str, Any]:
        self.drive_path_service.ensure_canonical_structure()
        db_root = self.drive_path_service.db_root
        checks: list[dict[str, Any]] = []
        errors: list[str] = []
        warnings: list[str] = []
        for folder in self.REQUIRED_DIRS:
            target = db_root / folder
            passed = target.exists()
            checks.append({"name": f"dir:{folder}", "passed": passed, "path": str(target)})
            if not passed:
                if folder in self.CRITICAL_DIRS:
                    errors.append(f"Missing canonical folder: {folder}")
                else:
                    warnings.append(f"Canonical folder not created yet: {folder}")
        required_files = [
            self.drive_path_service.get_notification_path("email_queue"),
            self.drive_path_service.get_registry_path("manufacturers"),
            self.drive_path_service.get_catalog_path("products"),
        ]
        for path in required_files:
            if not path.exists():
                warnings.append(f"Canonical file missing: {path}")
                continue
            try:
                self.json_service.read_json(path, {})
                checks.append({"name": f"json:{path.name}", "passed": True, "path": str(path)})
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Unreadable canonical JSON: {path} ({exc})")
        legacy_data_exists = any(self.governance_root.glob("*.json")) or any(self.public_buyers_root.glob("*.json"))
        canonical_registry = self.drive_path_service.get_registry_path("manufacturers")
        if legacy_data_exists and not canonical_registry.exists():
            warnings.append("Legacy data exists but canonical manufacturer registry is missing.")
        status = "PASS" if not errors else "FAIL"
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "rehearsal": rehearsal,
            "status": status,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "critical_errors": len(errors),
        }
        if persist:
            self._write_report(report, rehearsal=rehearsal)
        return report

    def _write_report(self, report: dict[str, Any], *, rehearsal: bool) -> Path:
        report_dir = self.runtime_root / "migration_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        prefix = "rehearsal_canonical_validation" if rehearsal else "canonical_validation"
        latest_name = "latest_rehearsal_canonical_validation_report.json" if rehearsal else "latest_canonical_validation_report.json"
        target = report_dir / f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        latest = report_dir / latest_name
        self.safe_drive_write_service.replace_document(target, report)
        self.safe_drive_write_service.replace_document(latest, report)
        return target
