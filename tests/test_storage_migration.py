from __future__ import annotations

import json
from pathlib import Path

from services.canonical_storage_validation_service import CanonicalStorageValidationService
from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.id_allocator_service import IdAllocatorService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.storage_migration_service import StorageMigrationService


def _build_services(tmp_path: Path):
    json_service = JsonService()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "runtime" / "backups",
        logging_service=LoggingService(tmp_path / "runtime" / "logs"),
        version_history_root=tmp_path / "runtime" / "version_history",
    )
    allocator = IdAllocatorService(tmp_path / "runtime" / "id_counters.json", FileLockService())
    drive_path_service = DrivePathService(
        db_root=tmp_path / "data" / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime",
        governance_root=tmp_path / "data" / "governance",
        manufacturers_root=tmp_path / "data" / "manufacturers",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        storage_mode="compatibility",
        allow_legacy_fallback=True,
    )
    migration_service = StorageMigrationService(
        drive_path_service=drive_path_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        governance_root=tmp_path / "data" / "governance",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        public_orders_root=tmp_path / "data" / "public_orders",
        public_payments_root=tmp_path / "data" / "public_payments",
        runtime_root=tmp_path / "runtime",
    )
    validator = CanonicalStorageValidationService(
        drive_path_service=drive_path_service,
        json_service=json_service,
        governance_root=tmp_path / "data" / "governance",
        public_buyers_root=tmp_path / "data" / "public_buyers",
    )
    return drive_path_service, migration_service, validator


def _seed_legacy(tmp_path: Path) -> None:
    governance = tmp_path / "data" / "governance"
    governance.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "public_buyers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "public_orders" / "2026-06").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "alerts").mkdir(parents=True, exist_ok=True)
    (governance / "manufacturers.json").write_text(
        json.dumps({"manufacturers": [{"manufacturer_code": "MANU101", "business_name": "Factory", "status": "ACTIVE"}]}),
        encoding="utf-8",
    )
    (governance / "products.json").write_text(
        json.dumps({"products": [{"product_id": "PRD1", "name": "Rice", "status": "ACTIVE"}]}),
        encoding="utf-8",
    )
    (tmp_path / "data" / "public_buyers" / "index.json").write_text(
        json.dumps({"buyers": [{"public_buyer_id": "PB001", "email": "buyer@example.com", "status": "ACTIVE"}]}),
        encoding="utf-8",
    )
    (tmp_path / "data" / "public_orders" / "2026-06" / "PUBORD-1.json").write_text(
        json.dumps({"public_order_id": "PUBORD-1", "status": "PAYMENT_PENDING", "created_at": "2026-06-02T10:00:00+00:00"}),
        encoding="utf-8",
    )
    (tmp_path / "runtime" / "alerts" / "alerts.json").write_text(
        json.dumps({"alerts": [{"alert_id": "ALERT1", "severity": "HIGH"}]}),
        encoding="utf-8",
    )


def test_dry_run_migration_writes_no_canonical_data(tmp_path):
    _seed_legacy(tmp_path)
    drive_path_service, migration_service, _validator = _build_services(tmp_path)
    report = migration_service.run(mode="dry_run")
    assert report["mode"] == "dry_run"
    assert not drive_path_service.get_registry_path("manufacturers").exists()


def test_execute_migration_writes_canonical_and_keeps_legacy(tmp_path):
    _seed_legacy(tmp_path)
    drive_path_service, migration_service, _validator = _build_services(tmp_path)
    report = migration_service.run(mode="execute")
    manufacturers = json.loads(drive_path_service.get_registry_path("manufacturers").read_text(encoding="utf-8"))
    assert report["records_migrated"] > 0
    assert manufacturers["manufacturers"][0]["id"] == "MANU101"
    assert (tmp_path / "data" / "governance" / "manufacturers.json").exists()


def test_duplicate_records_are_handled_safely(tmp_path):
    _seed_legacy(tmp_path)
    governance = tmp_path / "data" / "governance"
    (governance / "products.json").write_text(
        json.dumps({"products": [{"product_id": "PRD1", "name": "Rice"}, {"product_id": "PRD1", "name": "Rice 2"}]}),
        encoding="utf-8",
    )
    drive_path_service, migration_service, _validator = _build_services(tmp_path)
    migration_service.run(mode="execute")
    products = json.loads(drive_path_service.get_catalog_path("products").read_text(encoding="utf-8"))
    assert len(products["products"]) == 1


def test_migration_report_created(tmp_path):
    _seed_legacy(tmp_path)
    _drive_path_service, migration_service, _validator = _build_services(tmp_path)
    migration_service.run(mode="execute")
    report_path = tmp_path / "runtime" / "migration_reports" / "latest_migration_report.json"
    assert report_path.exists()


def test_canonical_validation_passes_after_execute(tmp_path):
    _seed_legacy(tmp_path)
    _drive_path_service, migration_service, validator = _build_services(tmp_path)
    migration_service.run(mode="execute")
    validation = validator.validate()
    assert validation["status"] in {"PASS", "REVIEW"}


def test_storage_mode_and_fallback_behavior(tmp_path):
    drive_path_service, _migration_service, _validator = _build_services(tmp_path)
    canonical = drive_path_service.get_registry_path("manufacturers")
    legacy = tmp_path / "data" / "governance" / "manufacturers.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("{}", encoding="utf-8")
    resolved = drive_path_service.resolve_preferred_path(canonical=canonical, legacy=legacy)
    assert resolved == legacy
    drive_path_service.set_storage_mode("canonical")
    resolved = drive_path_service.resolve_preferred_path(canonical=canonical, legacy=legacy, legacy_allowed=False)
    assert resolved == canonical
