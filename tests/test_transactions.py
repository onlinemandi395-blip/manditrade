from __future__ import annotations

import json

import pytest

from services.event_dispatcher import EventDispatcher
from services.file_lock_service import FileLockService
from services.gmail_service import GmailService
from services.id_allocator_service import IdAllocatorService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import FailingEventDispatcher, FailingSafeWriteService, GmailStub, LoggingStub, UploadedFileStub
from tests.helpers.fake_storage import JsonServiceStub
from tests.helpers.transaction_fixtures import (
    build_order_service,
    build_procurement_service,
    build_runtime,
    build_startup_recovery,
    current_user,
    seed_agreements,
    seed_inventory,
    seed_order,
    seed_procurement_request,
    tmp_path_from_runtime,
)


def test_id_allocator_generates_unique_ids_across_domains(tmp_path):
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    seen = {
        allocator.allocate("transaction"),
        allocator.allocate("transaction"),
        allocator.allocate("order"),
        allocator.allocate("agreement"),
        allocator.allocate("dispatch"),
        allocator.allocate("event"),
    }
    assert len(seen) == 6


def test_event_dispatcher_persists_standardized_event_model(tmp_path):
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    dispatcher = EventDispatcher(tmp_path / "events", id_allocator_service=allocator)
    event = dispatcher.emit(
        "ORDER_CREATED",
        {"transaction_id": "TXN-2026-000001", "correlation_id": "ORD-2026-000001", "order_id": "ORD-2026-000001"},
        producer="OrderTransactionService",
    )
    assert event["event_id"].startswith("EVT-")
    assert event["event_version"] == "1.0"
    assert event["transaction_id"] == "TXN-2026-000001"
    assert event["correlation_id"] == "ORD-2026-000001"
    assert len(list((tmp_path / "events").glob("*/*.json"))) == 1


def test_safe_write_replace_document_round_trip(tmp_path):
    target = tmp_path / "sample.json"
    service = SafeDriveWriteService(
        json_service=JsonServiceStub(),
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "version_history",
    )
    payload = {"schema_version": "1.0", "agreements": []}
    service.replace_document(target, payload)
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert "_version" in saved
    assert "document_hash" in saved


def test_procurement_rolls_back_when_pdf_generation_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    seed_procurement_request(runtime, "MANU101", requested_by="MANU999")
    seed_agreements(runtime, "MANU999")

    class FailingAgreementService:
        def __init__(self, base_service):
            self.base_service = base_service

        def create_procurement_agreement(self, **kwargs):
            return self.base_service.create_procurement_agreement(**kwargs)

        def confirm_advance(self, agreement, amount):
            return self.base_service.confirm_advance(agreement, amount)

        def generate_pdf(self, agreement, output_path):
            raise ValueError("forced pdf failure")

    base_agreement = build_order_service(runtime).agreement_service
    service = build_procurement_service(runtime, agreement_service=FailingAgreementService(base_agreement))
    with pytest.raises(ValueError, match="forced pdf failure"):
        service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
    inventory = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "inventory.json", {})
    procurement = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "procurement.json", {})
    agreements = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU999").shared_zone / "agreements.json", {})
    assert inventory["items"][0]["reserved_quantity"] == 0
    assert procurement["requests"][0]["status"] == "OPEN"
    assert agreements["agreements"] == []
    assert list((tmp_path / "events").glob("*/*.json")) == []


def test_procurement_rolls_back_when_agreement_append_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    seed_procurement_request(runtime, "MANU101", requested_by="MANU999")
    agreements_path = seed_agreements(runtime, "MANU999")
    failing_safe_write = FailingSafeWriteService(
        json_service=runtime["json_service"],
        file_lock_service=runtime["file_lock_service"],
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=runtime["logging_service"],
        version_history_root=tmp_path / "version_history",
        fail_on_append={str(agreements_path)},
    )
    service = build_procurement_service(runtime, safe_write=failing_safe_write)
    with pytest.raises(ValueError, match="forced append failure"):
        service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
    inventory = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "inventory.json", {})
    procurement = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "procurement.json", {})
    assert inventory["items"][0]["reserved_quantity"] == 0
    assert procurement["requests"][0]["status"] == "OPEN"


def test_duplicate_procurement_acceptance_is_blocked(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    seed_procurement_request(runtime, "MANU101", requested_by="MANU999")
    seed_agreements(runtime, "MANU999")
    service = build_procurement_service(runtime)
    result = service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
    assert result["status"] == "COMMITTED"
    with pytest.raises(ValueError, match="no longer OPEN"):
        service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)


def test_procurement_rolls_back_when_inventory_reservation_fails_after_validation(tmp_path):
    runtime = build_runtime(tmp_path)
    inventory_path = seed_inventory(runtime, "MANU101", quantity=100)
    seed_procurement_request(runtime, "MANU101", requested_by="MANU999")
    seed_agreements(runtime, "MANU999")
    failing_safe_write = FailingSafeWriteService(
        json_service=runtime["json_service"],
        file_lock_service=runtime["file_lock_service"],
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=runtime["logging_service"],
        version_history_root=tmp_path / "version_history",
        fail_on_mutate_targets={str(inventory_path)},
    )
    service = build_procurement_service(runtime, safe_write=failing_safe_write)
    with pytest.raises(ValueError, match="forced mutate failure"):
        service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
    inventory = runtime["json_service"].read_json(inventory_path, {})
    assert inventory["items"][0]["reserved_quantity"] == 0


def test_procurement_recovery_rolls_back_running_journal(tmp_path):
    runtime = build_runtime(tmp_path)
    inventory_path = seed_inventory(runtime, "MANU101", quantity=100)
    inventory = runtime["json_service"].read_json(inventory_path, {})
    runtime["safe_write"].backup_file(inventory_path)
    inventory["items"][0]["reserved_quantity"] = 20
    runtime["json_service"].write_json(inventory_path, inventory)
    transactions_dir = tmp_path_from_runtime(runtime) / "transactions"
    transactions_dir.mkdir(parents=True, exist_ok=True)
    journal = {
        "transaction_id": "TXN-2026-000001",
        "state": "RUNNING",
        "affected_files": [str(inventory_path)],
        "backup_targets": [str(inventory_path)],
        "rollback_cleanup_files": [],
        "created_at": "2026-05-23T00:00:00+00:00",
        "error_message": "",
    }
    (transactions_dir / "TXN-2026-000001.json").write_text(json.dumps(journal), encoding="utf-8")
    service = build_procurement_service(runtime)
    recovered = service.recover_incomplete_transactions()
    restored = runtime["json_service"].read_json(inventory_path, {})
    assert recovered[0]["state"] == "ROLLED_BACK"
    assert restored["items"][0]["reserved_quantity"] == 0


def test_dispatch_rolls_back_when_proof_storage_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="DISPATCH_READY")
    base_delivery = build_order_service(runtime).delivery_service

    class FailingDelivery:
        def build_dispatch_record(self, *args, **kwargs):
            return base_delivery.build_dispatch_record(*args, **kwargs)

        def save_delivery_proof(self, *_args, **_kwargs):
            raise ValueError("forced proof failure")

    service = build_order_service(runtime, delivery_service=FailingDelivery())
    with pytest.raises(ValueError, match="forced proof failure"):
        service.dispatch_order(current_user("MANU101"), "ORD-2026-000001", "MH12AB1234", "Driver", "Transport", UploadedFileStub("proof.jpg"))
    order = runtime["json_service"].read_json(order_path, {})
    assert order["status"] == "DISPATCH_READY"
    assert "dispatch" not in order


def test_duplicate_dispatch_is_blocked(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_order(runtime, "MANU101", status="DISPATCH_READY")
    service = build_order_service(runtime)
    service.dispatch_order(current_user("MANU101"), "ORD-2026-000001", "MH12AB1234", "Driver", "Transport")
    with pytest.raises(ValueError, match="DISPATCH_READY"):
        service.dispatch_order(current_user("MANU101"), "ORD-2026-000001", "MH12AB1234", "Driver", "Transport")


def test_dispatch_rolls_back_when_state_update_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="DISPATCH_READY")

    class FailingOrderStateService:
        def transition(self, order, next_status, actor, reason=None):
            if next_status == "DISPATCHED":
                raise ValueError("forced dispatch state failure")
            order["status"] = next_status
            return order

    service = build_order_service(runtime, order_state_service=FailingOrderStateService())
    with pytest.raises(ValueError, match="forced dispatch state failure"):
        service.dispatch_order(current_user("MANU101"), "ORD-2026-000001", "MH12AB1234", "Driver", "Transport")
    order = runtime["json_service"].read_json(order_path, {})
    assert order["status"] == "DISPATCH_READY"


def test_delivery_rolls_back_when_inventory_finalization_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="DISPATCHED")
    inventory_path = runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "inventory.json"
    failing_safe_write = FailingSafeWriteService(
        json_service=runtime["json_service"],
        file_lock_service=runtime["file_lock_service"],
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=runtime["logging_service"],
        version_history_root=tmp_path / "version_history",
        fail_on_mutate_targets={str(inventory_path)},
    )
    service = build_order_service(runtime, safe_write=failing_safe_write)
    with pytest.raises(ValueError, match="forced mutate failure"):
        service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="received")
    order = runtime["json_service"].read_json(order_path, {})
    inventory = runtime["json_service"].read_json(inventory_path, {})
    assert order["status"] == "DISPATCHED"
    assert inventory["items"][0]["reserved_quantity"] == 10


def test_duplicate_delivery_confirmation_is_blocked(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_order(runtime, "MANU101", status="DISPATCHED")
    service = build_order_service(runtime)
    service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="received")
    with pytest.raises(ValueError, match="DISPATCHED"):
        service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="received again")


def test_delivery_rolls_back_when_proof_upload_fails(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="DISPATCHED")
    base_delivery = build_order_service(runtime).delivery_service

    class FailingDelivery:
        def save_delivery_proof(self, *_args, **_kwargs):
            raise ValueError("forced delivery proof failure")

        def confirm_delivery(self, *args, **kwargs):
            return base_delivery.confirm_delivery(*args, **kwargs)

    service = build_order_service(runtime, delivery_service=FailingDelivery())
    with pytest.raises(ValueError, match="forced delivery proof failure"):
        service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", proof_file=UploadedFileStub("proof.png"))
    order = runtime["json_service"].read_json(order_path, {})
    assert order["status"] == "DISPATCHED"


def test_close_order_before_delivery_is_blocked(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_order(runtime, "MANU101", status="DISPATCHED")
    service = build_order_service(runtime)
    with pytest.raises(ValueError, match="Illegal transition"):
        service.close_order(current_user("MANU101"), "ORD-2026-000001")


def test_order_create_gmail_failure_does_not_rollback_commit(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    seed_agreements(runtime, "MANU101")
    gmail = GmailStub(fail_on_types={"order_confirmed"})
    service = build_order_service(runtime, gmail_service=gmail)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT-2026-000001", "email": "buyer@example.com"},
        {"product_code": "PRD101", "product_name": "Wheat", "mrp": 145},
        10,
    )
    order_path = runtime["drive"].resolve_orders_month_dir("MANU101", order["created_at"][:7]) / f"{order['order_id']}.json"
    assert runtime["json_service"].read_json(order_path, {})["status"] == "ADVANCE_PENDING"
    assert any(item["category"] == "notification_failures" for item in runtime["logging_service"].errors)


def test_order_create_event_failure_does_not_rollback_commit(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    seed_agreements(runtime, "MANU101")
    failing_dispatcher = FailingEventDispatcher(runtime["event_dispatcher"], {"ORDER_CREATED"})
    service = build_order_service(runtime, event_dispatcher=failing_dispatcher)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT-2026-000001", "email": "buyer@example.com"},
        {"product_code": "PRD101", "product_name": "Wheat", "mrp": 145},
        10,
    )
    order_path = runtime["drive"].resolve_orders_month_dir("MANU101", order["created_at"][:7]) / f"{order['order_id']}.json"
    assert runtime["json_service"].read_json(order_path, {})["status"] == "ADVANCE_PENDING"
    assert any(item["category"] == "event_failures" for item in runtime["logging_service"].errors)


def test_gmail_queue_creates_retry_record(tmp_path):
    class NoopLockService:
        def acquire(self, *_args, **_kwargs):
            return tmp_path / "noop.lock"

        def release(self, *_args, **_kwargs):
            return None

    queue_path = tmp_path / "queue" / "gmail_queue.json"
    service = GmailService("admin@example.com", use_gmail_api=True, queue_path=queue_path, safe_drive_write_service=SafeDriveWriteService(
        json_service=JsonServiceStub(),
        file_lock_service=NoopLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "version_history",
    ))
    service.enqueue_message("buyer@example.com", "Subject", "Body", "order_placed")
    service.send_message = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("smtp down"))  # type: ignore[method-assign]
    processed = service.process_queue()
    queue = JsonServiceStub().read_json(queue_path, {"messages": []})
    assert processed == 0
    assert queue["messages"][0]["status"] == "retry"
    assert queue["messages"][0]["retry_count"] == 1


def test_startup_recovery_cleans_stale_locks_and_quarantines_corrupt_journals(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=100)
    lock_target = runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "inventory.json"
    lock_path = runtime["file_lock_service"]._lock_path(lock_target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"target": str(lock_target), "owner": "test", "created_at_epoch": 0}), encoding="utf-8")
    procurement_service = build_procurement_service(runtime)
    order_service = build_order_service(runtime)
    bad_journal = tmp_path_from_runtime(runtime) / "transactions" / "TXN-2026-000999.json"
    bad_journal.parent.mkdir(parents=True, exist_ok=True)
    bad_journal.write_text("{bad json", encoding="utf-8")
    recovery = build_startup_recovery(runtime, procurement_service, order_service).run_recovery_pass()
    assert recovery["stale_locks_cleared"]
    assert any(item["state"] == "CORRUPTED" for item in recovery["procurement_recovered"])


def test_incomplete_order_transaction_recovery_restores_backup(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="DISPATCH_READY")
    runtime["safe_write"].backup_file(order_path)
    order = runtime["json_service"].read_json(order_path, {})
    order["status"] = "DISPATCHED"
    runtime["json_service"].write_json(order_path, order)
    journal_dir = tmp_path_from_runtime(runtime) / "order_transactions"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = {
        "transaction_id": "TXN-2026-000002",
        "state": "RUNNING",
        "order_id": "ORD-2026-000001",
        "affected_files": [str(order_path)],
        "backup_targets": [str(order_path)],
        "rollback_cleanup_files": [],
        "created_at": "2026-05-23T00:00:00+00:00",
        "error_message": "",
    }
    (journal_dir / "TXN-2026-000002.json").write_text(json.dumps(journal), encoding="utf-8")
    service = build_order_service(runtime)
    recovered = service.recover_incomplete_transactions()
    restored = runtime["json_service"].read_json(order_path, {})
    assert recovered[0]["state"] == "ROLLED_BACK"
    assert restored["status"] == "DISPATCH_READY"


def test_backup_restore_path_restores_latest_backup(tmp_path):
    json_service = JsonServiceStub()
    target = tmp_path / "sample.json"
    json_service.write_json(target, {"value": 1})
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "version_history",
    )
    safe_write.backup_file(target)
    json_service.write_json(target, {"value": 999})
    assert safe_write.restore_latest_backup(target) is True
    assert json_service.read_json(target, {})["value"] == 1


def test_two_same_stock_orders_do_not_overreserve_inventory(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", quantity=15)
    seed_agreements(runtime, "MANU101")
    service = build_order_service(runtime)
    first = service.create_order(
        "MANU101",
        {"client_id": "CLIENT-2026-000001", "email": "buyer@example.com"},
        {"product_code": "PRD101", "product_name": "Wheat", "mrp": 145},
        10,
    )
    second = service.create_order(
        "MANU101",
        {"client_id": "CLIENT-2026-000002", "email": "buyer2@example.com"},
        {"product_code": "PRD101", "product_name": "Wheat", "mrp": 145},
        10,
    )
    inventory = runtime["json_service"].read_json(runtime["drive"].get_manufacturer_paths("MANU101").shared_zone / "inventory.json", {})
    assert first["status"] == "ADVANCE_PENDING"
    assert second["status"] == "PROCUREMENT_REQUIRED"
    assert inventory["items"][0]["reserved_quantity"] == 10
