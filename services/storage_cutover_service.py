from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StorageCutoverService:
    INVALID_CANONICAL_MESSAGE = "Canonical storage mode requested, but validated migration report is missing."

    def __init__(
        self,
        *,
        runtime_root: Path,
        safe_drive_write_service,
        json_service,
    ) -> None:
        self.runtime_root = runtime_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service

    @property
    def migration_reports_dir(self) -> Path:
        target = self.runtime_root / "migration_reports"
        target.mkdir(parents=True, exist_ok=True)
        return target

    @property
    def release_reports_dir(self) -> Path:
        target = self.runtime_root / "release_reports"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def load_latest_migration_report(self, *, mode: str | None = None, rehearsal: bool | None = None) -> dict[str, Any]:
        if mode:
            prefix = "latest_rehearsal_" if rehearsal else "latest_"
            path = self.migration_reports_dir / f"{prefix}{mode}_migration_report.json"
        elif rehearsal:
            path = self.migration_reports_dir / "latest_rehearsal_migration_report.json"
        else:
            path = self.migration_reports_dir / "latest_migration_report.json"
        return self._read_report(path)

    def load_latest_validation_report(self, *, rehearsal: bool = False) -> dict[str, Any]:
        name = "latest_rehearsal_canonical_validation_report.json" if rehearsal else "latest_canonical_validation_report.json"
        return self._read_report(self.migration_reports_dir / name)

    def load_latest_readiness_report(self) -> dict[str, Any]:
        return self._read_report(self.release_reports_dir / "latest_storage_cutover_readiness.json")

    def evaluate_cutover_readiness(self, *, storage_mode_current: str = "compatibility") -> dict[str, Any]:
        migration_report = self.load_latest_migration_report(mode="execute", rehearsal=False)
        validation_report = self.load_latest_validation_report(rehearsal=False)
        critical_errors = list(validation_report.get("errors", []))
        warnings = list(validation_report.get("warnings", []))
        migration_pass = bool(migration_report) and migration_report.get("recommendation") == "PASS"
        validation_pass = bool(validation_report) and validation_report.get("status") == "PASS"
        legacy_counts = migration_report.get("legacy_counts", {}) if migration_report else {}
        canonical_counts = migration_report.get("canonical_counts", {}) if migration_report else {}
        records_discovered = int(migration_report.get("records_discovered", 0) or 0) if migration_report else 0
        migrated_total = sum(int(value or 0) for value in canonical_counts.values()) if canonical_counts else 0
        record_count_match = bool(migration_report) and records_discovered >= migrated_total and migrated_total > 0
        checksum_match = bool(migration_report) and bool(migration_report.get("checksum_summary")) and not migration_report.get("conflicts")
        if not migration_report:
            critical_errors.append("Missing execute migration report.")
        if not validation_report:
            critical_errors.append("Missing canonical validation report.")
        recommendation = "READY" if migration_pass and validation_pass and not critical_errors and record_count_match and checksum_match else "NOT_READY"
        recommended_next_action = "Switch storage.mode to canonical only after readiness is READY."
        if not migration_report:
            recommended_next_action = "Run execute migration first, then validate canonical storage."
        elif not validation_report:
            recommended_next_action = "Run canonical validation before requesting cutover."
        elif validation_report.get("status") != "PASS":
            recommended_next_action = "Resolve validation warnings/errors and rerun validation."
        elif migration_report.get("recommendation") != "PASS":
            recommended_next_action = "Resolve migration conflicts/errors before cutover."
        blocking_issues = []
        if not migration_pass:
            blocking_issues.append("Last execute migration report is not PASS.")
        if not validation_pass:
            blocking_issues.append("Canonical validation status is not PASS.")
        if critical_errors:
            blocking_issues.extend(critical_errors)
        if not record_count_match:
            blocking_issues.append("Canonical migrated counts do not fully match legacy discovery totals.")
        if not checksum_match:
            blocking_issues.append("Checksum or conflict validation is incomplete.")
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "storage_mode_current": storage_mode_current,
            "migration_pass": migration_pass,
            "validation_pass": validation_pass,
            "record_count_match": record_count_match,
            "checksum_match": checksum_match,
            "critical_errors": critical_errors,
            "warnings": warnings,
            "recommendation": recommendation,
            "blocking_issues": blocking_issues,
            "recommended_next_action": recommended_next_action,
            "migration_report": migration_report,
            "validation_report": validation_report,
            "legacy_record_groups": len(legacy_counts),
            "canonical_record_groups": len(canonical_counts),
        }

    def generate_cutover_readiness_report(self, *, storage_mode_current: str = "compatibility") -> dict[str, Any]:
        report = self.evaluate_cutover_readiness(storage_mode_current=storage_mode_current)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target = self.release_reports_dir / f"storage_cutover_readiness_{timestamp}.json"
        latest = self.release_reports_dir / "latest_storage_cutover_readiness.json"
        self.safe_drive_write_service.replace_document(target, report)
        self.safe_drive_write_service.replace_document(latest, report)
        return report

    def canonical_mode_blockers(self) -> list[str]:
        report = self.evaluate_cutover_readiness(storage_mode_current="canonical")
        if report["recommendation"] == "READY":
            return []
        return [self.INVALID_CANONICAL_MESSAGE]

    def _read_report(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return self.json_service.read_json(path, {})
