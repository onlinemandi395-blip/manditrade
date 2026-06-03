from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.file_lock_service import FileLockService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.storage_cutover_service import StorageCutoverService
from utils.config_loader import load_config
from utils.paths import APP_RUNTIME_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_VERSION_HISTORY_DIR


def main() -> int:
    system_config = load_config("system_config.json")
    safe_write = SafeDriveWriteService(
        json_service=JsonService(),
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=RUNTIME_BACKUPS_DIR,
        logging_service=LoggingService(APP_RUNTIME_DIR / "logs"),
        version_history_root=RUNTIME_VERSION_HISTORY_DIR,
    )
    service = StorageCutoverService(
        runtime_root=APP_RUNTIME_DIR,
        safe_drive_write_service=safe_write,
        json_service=JsonService(),
    )
    report = service.generate_cutover_readiness_report(
        storage_mode_current=str(system_config.get("storage", {}).get("mode", "compatibility")),
    )
    print(json.dumps(report, indent=2))
    return 0 if report["recommendation"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
