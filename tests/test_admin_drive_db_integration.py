from __future__ import annotations

from pathlib import Path

from services.admin_drive_database_service import AdminDriveDatabaseService
from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService


def _build_service(tmp_path: Path, *, storage_mode: str = "compatibility") -> AdminDriveDatabaseService:
    json_service = JsonService()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "runtime" / "backups",
        logging_service=LoggingService(tmp_path / "runtime" / "logs"),
        version_history_root=tmp_path / "runtime" / "history",
    )
    drive_path_service = DrivePathService(
        db_root=tmp_path / "data" / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime",
        governance_root=tmp_path / "data" / "governance",
        manufacturers_root=tmp_path / "data" / "manufacturers",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        storage_mode=storage_mode,
        allow_legacy_fallback=True,
    )
    return AdminDriveDatabaseService(
        drive_path_service=drive_path_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        runtime_root=tmp_path / "runtime",
        system_config={"storage": {"mode": storage_mode, "admin_drive_db_enabled": True, "admin_db_root_folder_name": "MANDITRADE_DB"}},
        secret_overrides={"google_drive": {"admin_db_root_folder_name": "MANDITRADE_DB"}},
    )


def test_admin_db_root_resolves_from_secret_override(tmp_path):
    service = _build_service(tmp_path)
    resolved = service.resolve_root_config()

    assert resolved["root_folder_name"] == "MANDITRADE_DB"
    assert resolved["source"] == "streamlit_secrets"


def test_admin_drive_bootstrap_dry_run_writes_nothing(tmp_path):
    service = _build_service(tmp_path)
    report = service.bootstrap(dry_run=True)

    assert report["mode"] == "dry_run"
    assert not service.drive_path_service.db_root.exists()


def test_admin_drive_bootstrap_execute_creates_expected_metadata(tmp_path):
    service = _build_service(tmp_path)
    report = service.bootstrap(dry_run=False)

    assert report["mode"] == "execute"
    assert service.drive_path_service.get_registry_path("manufacturers").exists()
    assert service.drive_path_service.get_notification_path("email_queue").exists()


def test_default_json_envelopes_are_valid(tmp_path):
    service = _build_service(tmp_path)
    service.bootstrap(dry_run=False)
    payload = service.json_service.read_json(service.drive_path_service.get_registry_path("manufacturers"), {})

    assert payload["schema_version"] == 1
    assert "manufacturers" in payload


def test_domain_paths_resolve_under_admin_root(tmp_path):
    service = _build_service(tmp_path)
    path = service.drive_path_service.path("orders.marketplace", year_month="2026-06")

    assert "MANDITRADE_DB" in str(path)
    assert "05_orders" in str(path)


def test_canonical_mode_blocks_invalid_admin_drive_db(tmp_path):
    service = _build_service(tmp_path, storage_mode="canonical")

    assert service.canonical_mode_blockers() == [AdminDriveDatabaseService.INVALID_CANONICAL_MESSAGE]


def test_canonical_mode_allows_valid_admin_drive_db(tmp_path):
    service = _build_service(tmp_path, storage_mode="canonical")
    service.bootstrap(dry_run=False)
    service.validate_database_tree(persist=True)

    assert service.canonical_mode_blockers() == []


def test_month_partition_and_media_folder_helpers_work(tmp_path):
    service = _build_service(tmp_path)
    order_path = service.drive_path_service.get_order_path("marketplace", "2026-06")
    media_folder = service.drive_path_service.get_media_folder("payment_proof")

    assert "2026-06" in str(order_path)
    assert media_folder.name == "payment_proofs"


def test_system_health_contains_admin_drive_db_panel():
    content = Path("modules/system/health_dashboard.py").read_text(encoding="utf-8")

    assert "Admin Drive Database" in content
    assert "Validate Admin Drive DB" in content
