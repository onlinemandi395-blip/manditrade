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
from services.storage_cutover_service import StorageCutoverService
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
    live_drive_paths = DrivePathService(
        db_root=tmp_path / "data" / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime",
        governance_root=tmp_path / "data" / "governance",
        manufacturers_root=tmp_path / "data" / "manufacturers",
        public_buyers_root=tmp_path / "data" / "public_buyers",
    )
    rehearsal_drive_paths = DrivePathService(
        db_root=tmp_path / "runtime" / "migration_rehearsal" / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime" / "migration_rehearsal",
        governance_root=tmp_path / "data" / "governance",
        manufacturers_root=tmp_path / "data" / "manufacturers",
        public_buyers_root=tmp_path / "data" / "public_buyers",
    )
    migration_service = StorageMigrationService(
        drive_path_service=live_drive_paths,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=IdAllocatorService(tmp_path / "runtime" / "id_counters.json", FileLockService()),
        governance_root=tmp_path / "data" / "governance",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        public_orders_root=tmp_path / "data" / "public_orders",
        public_payments_root=tmp_path / "data" / "public_payments",
        runtime_root=tmp_path / "runtime",
    )
    rehearsal_migration_service = StorageMigrationService(
        drive_path_service=rehearsal_drive_paths,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=IdAllocatorService(tmp_path / "runtime" / "id_counters.json", FileLockService()),
        governance_root=tmp_path / "data" / "governance",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        public_orders_root=tmp_path / "data" / "public_orders",
        public_payments_root=tmp_path / "data" / "public_payments",
        runtime_root=tmp_path / "runtime" / "migration_rehearsal",
    )
    validator = CanonicalStorageValidationService(
        drive_path_service=live_drive_paths,
        json_service=json_service,
        governance_root=tmp_path / "data" / "governance",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        runtime_root=tmp_path / "runtime",
        safe_drive_write_service=safe_write,
    )
    cutover_service = StorageCutoverService(
        runtime_root=tmp_path / "runtime",
        safe_drive_write_service=safe_write,
        json_service=json_service,
    )
    return migration_service, rehearsal_migration_service, validator, cutover_service


def _seed_legacy(tmp_path: Path) -> None:
    governance = tmp_path / "data" / "governance"
    governance.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "public_buyers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "public_orders").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "public_payments").mkdir(parents=True, exist_ok=True)
    (governance / "manufacturers.json").write_text(
        json.dumps({"manufacturers": [{"manufacturer_code": "MANU101", "business_name": "Factory", "status": "ACTIVE"}]}),
        encoding="utf-8",
    )
    (governance / "products.json").write_text(
        json.dumps({"products": [{"product_id": "PRD1", "name": "Rice", "status": "ACTIVE"}]}),
        encoding="utf-8",
    )


def test_rehearsal_writes_separate_reports(tmp_path):
    _seed_legacy(tmp_path)
    _migration_service, rehearsal_service, _validator, _cutover_service = _build_services(tmp_path)
    rehearsal_service.run(mode="execute", rehearsal=True, report_dir=tmp_path / "runtime" / "migration_reports")
    latest_path = tmp_path / "runtime" / "migration_reports" / "latest_rehearsal_execute_migration_report.json"
    assert latest_path.exists()
    rehearsal_db = tmp_path / "runtime" / "migration_rehearsal" / "MANDITRADE_DB"
    assert rehearsal_db.exists()
    assert not (tmp_path / "data" / "MANDITRADE_DB" / "registry" / "manufacturers.json").exists()


def test_cutover_guard_blocks_invalid_canonical_mode(tmp_path):
    _seed_legacy(tmp_path)
    _migration_service, _rehearsal_service, _validator, cutover_service = _build_services(tmp_path)
    blockers = cutover_service.canonical_mode_blockers()
    assert blockers == [StorageCutoverService.INVALID_CANONICAL_MESSAGE]


def test_canonical_mode_allowed_after_pass_report(tmp_path):
    _seed_legacy(tmp_path)
    migration_service, _rehearsal_service, validator, cutover_service = _build_services(tmp_path)
    migration_service.run(mode="execute")
    validator.validate()
    assert cutover_service.canonical_mode_blockers() == []


def test_readiness_report_not_ready_if_validation_missing(tmp_path):
    _seed_legacy(tmp_path)
    migration_service, _rehearsal_service, _validator, cutover_service = _build_services(tmp_path)
    migration_service.run(mode="execute")
    readiness = cutover_service.generate_cutover_readiness_report(storage_mode_current="compatibility")
    assert readiness["recommendation"] == "NOT_READY"


def test_readiness_report_ready_after_pass(tmp_path):
    _seed_legacy(tmp_path)
    migration_service, _rehearsal_service, validator, cutover_service = _build_services(tmp_path)
    migration_service.run(mode="execute")
    validator.validate()
    readiness = cutover_service.generate_cutover_readiness_report(storage_mode_current="compatibility")
    assert readiness["recommendation"] == "READY"


def test_legacy_data_remains_untouched_after_rehearsal(tmp_path):
    _seed_legacy(tmp_path)
    legacy_path = tmp_path / "data" / "governance" / "manufacturers.json"
    before = legacy_path.read_text(encoding="utf-8")
    _migration_service, rehearsal_service, _validator, _cutover_service = _build_services(tmp_path)
    rehearsal_service.run(mode="execute", rehearsal=True, report_dir=tmp_path / "runtime" / "migration_reports")
    after = legacy_path.read_text(encoding="utf-8")
    assert before == after
