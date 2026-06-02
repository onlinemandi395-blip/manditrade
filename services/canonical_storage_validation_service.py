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

    def __init__(self, *, drive_path_service, json_service, governance_root: Path, public_buyers_root: Path) -> None:
        self.drive_path_service = drive_path_service
        self.json_service = json_service
        self.governance_root = governance_root
        self.public_buyers_root = public_buyers_root

    def validate(self) -> dict[str, Any]:
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
        if not errors and warnings:
            status = "REVIEW"
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": status,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }
