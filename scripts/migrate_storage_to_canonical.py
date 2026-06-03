from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.id_allocator_service import IdAllocatorService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.storage_migration_service import StorageMigrationService
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, DATA_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_VERSION_HISTORY_DIR


def _build_service(*, rehearsal: bool = False) -> StorageMigrationService:
    json_service = JsonService()
    runtime_root = APP_RUNTIME_DIR / "migration_rehearsal" if rehearsal else APP_RUNTIME_DIR
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=RUNTIME_BACKUPS_DIR,
        logging_service=LoggingService(APP_RUNTIME_DIR / "logs"),
        version_history_root=RUNTIME_VERSION_HISTORY_DIR,
    )
    allocator = IdAllocatorService(APP_RUNTIME_DIR / "id_counters.json", FileLockService())
    drive_path_service = DrivePathService(
        db_root=(runtime_root / "MANDITRADE_DB") if rehearsal else (DATA_DIR / "MANDITRADE_DB"),
        runtime_root=runtime_root,
        governance_root=GOVERNANCE_DIR,
        manufacturers_root=MANUFACTURERS_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
    )
    return StorageMigrationService(
        drive_path_service=drive_path_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        governance_root=GOVERNANCE_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
        public_orders_root=BASE_DIR / "data" / "public_orders",
        public_payments_root=BASE_DIR / "data" / "public_payments",
        runtime_root=runtime_root,
    )


def main(argv: list[str]) -> int:
    mode = "dry_run"
    rehearsal = "--rehearsal" in argv
    if "--execute" in argv:
        mode = "execute"
    service = _build_service(rehearsal=rehearsal)
    report = service.run(mode=mode, rehearsal=rehearsal)
    print(json.dumps(report, indent=2))
    return 0 if report["recommendation"] in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
