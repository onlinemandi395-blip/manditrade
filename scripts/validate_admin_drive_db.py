from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.admin_drive_database_service import AdminDriveDatabaseService
from services.auth_service import AuthService
from services.drive_path_service import DrivePathService
from services.drive_service import DriveService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.security_service import SecurityService
from utils.config_loader import load_config
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, DATA_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_TOKENS_DIR, RUNTIME_VERSION_HISTORY_DIR


def _build_service() -> AdminDriveDatabaseService:
    json_service = JsonService()
    system_config = load_config("system_config.json")
    oauth_config = load_config("oauth_config.json")
    if "google" in st.secrets:
        google_secret_overrides = dict(st.secrets["google"])
        oauth_config["google_oauth"]["client_id"] = google_secret_overrides.get("client_id", oauth_config["google_oauth"]["client_id"])
        oauth_config["google_oauth"]["client_secret"] = google_secret_overrides.get("client_secret", oauth_config["google_oauth"]["client_secret"])
        oauth_config["google_oauth"]["redirect_uri"] = google_secret_overrides.get("redirect_uri", oauth_config["google_oauth"]["redirect_uri"])
    google_drive_secret_overrides = dict(st.secrets["google_drive"]) if "google_drive" in st.secrets else {}
    service_account_present = bool(
        str(google_drive_secret_overrides.get("service_account_json", "") or "").strip()
        or str(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "") or "").strip()
        or str(system_config.get("storage", {}).get("service_account_json", "") or "").strip()
    )
    root_name = str(
        google_drive_secret_overrides.get("admin_db_root_folder_name")
        or system_config.get("storage", {}).get("admin_db_root_folder_name")
        or "MANDITRADE_DB"
    ).strip() or "MANDITRADE_DB"
    auth_service = AuthService(oauth_config=oauth_config, enable_mock_auth=system_config.get("security", {}).get("enable_mock_auth", False))
    security_service = SecurityService(
        encryption_service=EncryptionService(secret_seed=system_config.get("app", {}).get("name", "MandiTrade")),
        auth_service=auth_service,
        admin_token_file=BASE_DIR / system_config.get("security", {}).get("admin_token_file", "configs/admin_token.enc"),
        manufacturer_token_dir=BASE_DIR / system_config.get("security", {}).get("manufacturer_token_dir", "data/runtime/manufacturer_tokens"),
        runtime_tokens_dir=RUNTIME_TOKENS_DIR,
        require_verification_for_admin_runtime=system_config.get("security", {}).get("require_verification_for_admin_runtime", True),
    )
    drive_service = DriveService(
        local_root=MANUFACTURERS_DIR,
        manufacturer_root_prefix=system_config.get("storage", {}).get("manufacturer_root_prefix", "MANDITRADE_"),
        shared_zone_name=system_config.get("storage", {}).get("shared_zone_name", "shared_zone"),
        private_zone_name=system_config.get("storage", {}).get("private_zone_name", "private_zone"),
        use_drive_api=bool(system_config.get("storage", {}).get("use_drive_api", False) or service_account_present),
        safe_drive_write_service=None,
        logging_service=None,
        runtime_metrics_service=None,
    )
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
        drive_service=drive_service,
        security_service=security_service,
        auth_service=auth_service,
    )


def main(argv: list[str]) -> int:
    report = _build_service().validate_database_tree(persist=True)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
