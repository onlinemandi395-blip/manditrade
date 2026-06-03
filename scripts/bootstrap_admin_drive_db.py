from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.admin_drive_database_service import AdminDriveDatabaseService
from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from utils.config_loader import load_config
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, DATA_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_VERSION_HISTORY_DIR


def _build_service() -> AdminDriveDatabaseService:
    json_service = JsonService()
    system_config = load_config("system_config.json")
    google_drive_secret_overrides = dict(st.secrets["google_drive"]) if "google_drive" in st.secrets else {}
    root_name = str(
        google_drive_secret_overrides.get("admin_db_root_folder_name")
        or system_config.get("storage", {}).get("admin_db_root_folder_name")
        or "MANDITRADE_DB"
    ).strip() or "MANDITRADE_DB"
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=RUNTIME_BACKUPS_DIR,
        logging_service=LoggingService(APP_RUNTIME_DIR / "logs"),
        version_history_root=RUNTIME_VERSION_HISTORY_DIR,
    )
    return AdminDriveDatabaseService(
        drive_path_service=DrivePathService(
            db_root=DATA_DIR / root_name,
            runtime_root=APP_RUNTIME_DIR,
            governance_root=GOVERNANCE_DIR,
            manufacturers_root=MANUFACTURERS_DIR,
            public_buyers_root=BASE_DIR / "data" / "public_buyers",
            storage_mode=system_config.get("storage", {}).get("mode", "compatibility"),
            allow_legacy_fallback=bool(system_config.get("storage", {}).get("allow_legacy_fallback", True)),
        ),
        safe_drive_write_service=safe_write,
        json_service=json_service,
        runtime_root=APP_RUNTIME_DIR,
        system_config=system_config,
        secret_overrides={"google_drive": google_drive_secret_overrides},
    )


def main(argv: list[str]) -> int:
    dry_run = "--execute" not in argv
    service = _build_service()
    if "--structure-report" in argv:
        report = service.generate_structure_report()
    else:
        report = service.bootstrap(dry_run=dry_run)
    print(json.dumps(report, indent=2))
    return 0 if report.get("recommendation", "PASS") in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
