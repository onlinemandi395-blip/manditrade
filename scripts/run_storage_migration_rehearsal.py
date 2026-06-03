from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.canonical_storage_validation_service import CanonicalStorageValidationService
from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.id_allocator_service import IdAllocatorService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.storage_migration_service import StorageMigrationService
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_VERSION_HISTORY_DIR


def _build_safe_write(json_service: JsonService) -> SafeDriveWriteService:
    return SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=RUNTIME_BACKUPS_DIR,
        logging_service=LoggingService(APP_RUNTIME_DIR / "logs"),
        version_history_root=RUNTIME_VERSION_HISTORY_DIR,
    )


def _build_migration_service(*, rehearsal: bool, json_service: JsonService, safe_write: SafeDriveWriteService) -> StorageMigrationService:
    runtime_root = APP_RUNTIME_DIR / "migration_rehearsal" if rehearsal else APP_RUNTIME_DIR
    drive_path_service = DrivePathService(
        db_root=(runtime_root / "MANDITRADE_DB") if rehearsal else (BASE_DIR / "data" / "MANDITRADE_DB"),
        runtime_root=runtime_root,
        governance_root=GOVERNANCE_DIR,
        manufacturers_root=MANUFACTURERS_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
    )
    return StorageMigrationService(
        drive_path_service=drive_path_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=IdAllocatorService(APP_RUNTIME_DIR / "id_counters.json", FileLockService()),
        governance_root=GOVERNANCE_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
        public_orders_root=BASE_DIR / "data" / "public_orders",
        public_payments_root=BASE_DIR / "data" / "public_payments",
        runtime_root=runtime_root,
    )


def _build_validation_service(*, json_service: JsonService, safe_write: SafeDriveWriteService) -> CanonicalStorageValidationService:
    rehearsal_root = APP_RUNTIME_DIR / "migration_rehearsal"
    return CanonicalStorageValidationService(
        drive_path_service=DrivePathService(
            db_root=rehearsal_root / "MANDITRADE_DB",
            runtime_root=rehearsal_root,
            governance_root=GOVERNANCE_DIR,
            manufacturers_root=MANUFACTURERS_DIR,
            public_buyers_root=BASE_DIR / "data" / "public_buyers",
        ),
        json_service=json_service,
        governance_root=GOVERNANCE_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
        runtime_root=APP_RUNTIME_DIR,
        safe_drive_write_service=safe_write,
    )


def main() -> int:
    json_service = JsonService()
    safe_write = _build_safe_write(json_service)
    live_migration = _build_migration_service(rehearsal=False, json_service=json_service, safe_write=safe_write)
    rehearsal_migration = _build_migration_service(rehearsal=True, json_service=json_service, safe_write=safe_write)
    validator = _build_validation_service(json_service=json_service, safe_write=safe_write)

    dry_run_report = live_migration.run(mode="dry_run")
    execute_report = rehearsal_migration.run(mode="execute", rehearsal=True)
    validation_report = validator.validate(rehearsal=True)

    rehearsal_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "steps": {
            "dry_run": dry_run_report,
            "execute_rehearsal": execute_report,
            "validation_rehearsal": validation_report,
        },
        "recommendation": "PASS"
        if dry_run_report.get("recommendation") in {"PASS", "REVIEW"}
        and execute_report.get("recommendation") == "PASS"
        and validation_report.get("status") == "PASS"
        else "REVIEW",
    }
    report_dir = APP_RUNTIME_DIR / "migration_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    target = report_dir / f"rehearsal_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    safe_write.replace_document(target, rehearsal_report)
    safe_write.replace_document(report_dir / "latest_rehearsal_workflow_report.json", rehearsal_report)
    print(json.dumps(rehearsal_report, indent=2))
    return 0 if rehearsal_report["recommendation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
