from __future__ import annotations

import json
from datetime import date, timedelta
from types import SimpleNamespace

from services.action_center_service import ActionCenterService
from services.event_dispatcher import EventDispatcher
from services.file_lock_service import FileLockService
from services.gmail_service import GmailService
from services.id_allocator_service import IdAllocatorService
from services.ledger_reminder_service import LedgerReminderService
from services.notification_center_service import NotificationCenterService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import GmailStub, LoggingStub
from tests.helpers.fake_storage import JsonServiceStub
from tests.helpers.transaction_fixtures import build_order_service, build_procurement_service, build_runtime, current_user, seed_inventory, seed_order, seed_rfq_doc, tmp_path_from_runtime


def test_id_allocator_generates_unique_ids_across_new_domains(tmp_path):
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    seen = {
        allocator.allocate("transaction"),
        allocator.allocate("order"),
        allocator.allocate("product"),
        allocator.allocate("rfq"),
        allocator.allocate("response"),
        allocator.allocate("confirmation"),
        allocator.allocate("ledger_entry"),
        allocator.allocate("notification"),
    }
    assert len(seen) == 8


def test_event_dispatcher_persists_standardized_event_model(tmp_path):
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    dispatcher = EventDispatcher(tmp_path / "events", id_allocator_service=allocator)
    event = dispatcher.emit("ORDER_CREATED", {"transaction_id": "TXN-2026-000001", "correlation_id": "ORD-2026-000001", "order_id": "ORD-2026-000001"}, producer="OrderTransactionService")
    assert event["event_id"].startswith("EVT-")
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
    payload = {"schema_version": "2.0", "notifications": []}
    service.replace_document(target, payload)
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert "_version" in saved


def test_dual_inventory_reserve_from_self_inventory(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=100, mandi_qty=25)
    service = build_order_service(runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 20, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        {"payment_modes": ["cash"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "30% upfront"},
    )
    inventory = runtime["json_service"].read_json(runtime["domain_paths"].inventory_path("MANU101"), {})
    assert order["status"] == "READY_TO_CONFIRM"
    assert inventory["items"][0]["self_inventory"]["reserved_qty"] == 20


def test_mandi_inventory_reserve_for_rfq_response(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU202", self_qty=20, mandi_qty=70)
    seed_rfq_doc(runtime, "MANU101")
    procurement = build_procurement_service(runtime)
    rfq = procurement.create_rfq_from_shortage(manufacturer_code="MANU101", items=[{"product_id": "PRD-2026-000001", "required_qty": 40, "unit": "kg"}], trade_terms={"payment_modes": ["cash"], "upfront_percentage": 40, "ledger_days": 15, "freestyle_description": "urgent"})
    response = procurement.respond_to_rfq(
        current_user("MANU202", "supplier@example.com"),
        "MANU101",
        rfq["rfq_id"],
        [{"product_id": "PRD-2026-000001", "qty": 40, "unit": "kg"}],
        {"upfront_percentage": 50, "ledger_days": 7, "freestyle_note": "Can dispatch today"},
    )
    inventory = runtime["json_service"].read_json(runtime["domain_paths"].inventory_path("MANU202"), {})
    assert response["status"] == "SUBMITTED"
    assert inventory["items"][0]["mandi_inventory"]["reserved_qty"] == 40


def test_self_to_mandi_transfer(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=100, mandi_qty=10)
    dual = build_order_service(runtime).dual_inventory_service
    dual.transfer_self_to_mandi("MANU101", "PRD-2026-000001", 25)
    inventory = runtime["json_service"].read_json(runtime["domain_paths"].inventory_path("MANU101"), {})
    assert inventory["items"][0]["self_inventory"]["available_qty"] == 75
    assert inventory["items"][0]["mandi_inventory"]["available_qty"] == 35


def test_mandi_to_self_withdraw(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=100, mandi_qty=30)
    dual = build_order_service(runtime).dual_inventory_service
    dual.withdraw_mandi_to_self("MANU101", "PRD-2026-000001", 10)
    inventory = runtime["json_service"].read_json(runtime["domain_paths"].inventory_path("MANU101"), {})
    assert inventory["items"][0]["self_inventory"]["available_qty"] == 110
    assert inventory["items"][0]["mandi_inventory"]["available_qty"] == 20


def test_multi_product_client_order_and_payment_proposal(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", product_id="PRD-2026-000001", self_qty=100, mandi_qty=20)
    build_order_service(runtime).dual_inventory_service.upsert_inventory_item("MANU101", product_id="PRD-2026-000002", product_name="Wheat", unit="kg", self_available_qty=80, mandi_available_qty=10)
    service = build_order_service(runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [
            {"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 10, "unit": "kg", "mrp": 50, "mandi_price": 40},
            {"product_id": "PRD-2026-000002", "product_name": "Wheat", "qty": 15, "unit": "kg", "mrp": 45, "mandi_price": 35},
        ],
        {"payment_modes": ["cash", "upi"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "30% upfront online"},
    )
    assert len(order["items"]) == 2
    assert order["payment_proposal"]["payment_modes"] == ["cash", "upi"]


def test_partial_shortage_creates_rfq(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=15, mandi_qty=0)
    service = build_order_service(runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 20, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        {"payment_modes": ["cash"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "Need partial udhar"},
    )
    rfqs = build_procurement_service(runtime).list_requests("MANU101")
    assert order["status"] == "PROCUREMENT_REQUIRED"
    assert rfqs[0]["items"][0]["required_qty"] == 5


def test_rfq_response_with_freestyle_terms(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU202", self_qty=10, mandi_qty=100)
    seed_rfq_doc(runtime, "MANU101")
    procurement = build_procurement_service(runtime)
    rfq = procurement.create_rfq_from_shortage(manufacturer_code="MANU101", items=[{"product_id": "PRD-2026-000001", "required_qty": 20, "unit": "kg"}], trade_terms={"payment_modes": ["online"], "upfront_percentage": 40, "ledger_days": 15, "freestyle_description": "urgent"})
    response = procurement.respond_to_rfq(current_user("MANU202", "supplier@example.com"), "MANU101", rfq["rfq_id"], [{"product_id": "PRD-2026-000001", "qty": 20, "unit": "kg"}], {"upfront_percentage": 50, "ledger_days": 7, "freestyle_note": "Dispatch today"})
    assert response["supplier_terms"]["freestyle_note"] == "Dispatch today"


def test_ledger_entry_creation_on_order_confirmation(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=100, mandi_qty=0)
    service = build_order_service(runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 20, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        {"payment_modes": ["cash"], "upfront_percentage": 40, "ledger_days": 10, "freestyle_note": "40% paid"},
    )
    confirmed = service.confirm_order(current_user("MANU101"), order["order_id"])
    ledgers = service.ledger_service.list_ledgers("MANU101")
    assert confirmed["status"] == "CONFIRMED"
    assert ledgers[0]["entries"][0]["paid_amount"] == 400.0


def test_payment_reminder_duplicate_prevention(tmp_path):
    runtime = build_runtime(tmp_path)
    service = build_order_service(runtime)
    entry = service.ledger_service.create_entry("MANU101", party_a="MANU101", party_b="CLIENT101", entry_type="ORDER_SUPPLIED", amount=1000, paid_amount=0, ledger_days=0, note="due now")
    ledger_path = runtime["domain_paths"].ledger_path("MANU101")
    payload = runtime["json_service"].read_json(ledger_path, {})
    payload["ledgers"][0]["entries"][0]["due_date"] = date.today().isoformat()
    runtime["json_service"].write_json(ledger_path, payload)
    reminder = LedgerReminderService(GmailStub(), service.ledger_service, runtime["safe_write"], runtime["domain_paths"], runtime["json_service"], {"ledger_reminders": {"enabled": True, "upcoming_days_before": 3, "final_reminder_after_days": 15, "max_reminders_per_due": 4}})
    first = reminder.run_for_manufacturer("MANU101", "buyer@example.com")
    second = reminder.run_for_manufacturer("MANU101", "buyer@example.com")
    assert entry["entry_id"].startswith("LEDENT-")
    assert first == 1
    assert second == 0


def test_my_actions_aggregation(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_inventory(runtime, "MANU101", self_qty=8, mandi_qty=0)
    service = build_order_service(runtime)
    service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 5, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        {"payment_modes": ["cash"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "30% upfront"},
    )
    action_center = ActionCenterService(
        governance_service=SimpleNamespace(list_manufacturers=lambda: [], list_products=lambda: []),
        gmail_service=GmailStub(),
        notification_center_service=service.notification_center_service,
        ledger_service=service.ledger_service,
        order_query_service=SimpleNamespace(list_orders=lambda manufacturer_code: [service.drive_service.json_service.read_json(path, {}) for path in runtime["drive"].resolve_orders_month_dir(manufacturer_code, date.today().strftime("%Y-%m")).glob("*.json")], list_orders_for_client=lambda manufacturer_code, client_email: []),
        procurement_query_service=SimpleNamespace(list_procurement_requests=lambda manufacturer_code: []),
        dual_inventory_service=service.dual_inventory_service,
    )
    actions = action_center.get_actions(current_user("MANU101"))
    assert any(item["type"] == "LOW_INVENTORY" for item in actions)


def test_notification_creation(tmp_path):
    runtime = build_runtime(tmp_path)
    center = NotificationCenterService(runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    notification = center.create_notification("MANU101", user_id="MANU101", notification_type="RFQ_ACCEPTED", priority="HIGH", title="RFQ Accepted", message="A supplier accepted your rice request.", source_type="RFQ", source_id="RFQ-2026-000001")
    notifications = center.list_notifications("MANU101")
    assert notification["notification_id"].startswith("NOTIF-")
    assert len(notifications) == 1


def test_dispatch_and_delivery_flow_still_finalize_inventory(tmp_path):
    runtime = build_runtime(tmp_path)
    seed_order(runtime, "MANU101", status="CONFIRMED", reserved_qty=10)
    service = build_order_service(runtime)
    service.dispatch_order(current_user("MANU101"), "ORD-2026-000001", "MH12AB1234", "Driver", "Transport")
    delivered = service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="received")
    inventory = runtime["json_service"].read_json(runtime["domain_paths"].inventory_path("MANU101"), {})
    assert delivered["status"] == "DELIVERED"
    assert inventory["items"][0]["self_inventory"]["reserved_qty"] == 0


def test_incomplete_order_transaction_recovery_restores_backup(tmp_path):
    runtime = build_runtime(tmp_path)
    order_path = seed_order(runtime, "MANU101", status="CONFIRMED")
    runtime["safe_write"].backup_file(order_path)
    order = runtime["json_service"].read_json(order_path, {})
    order["status"] = "DISPATCHED"
    runtime["json_service"].write_json(order_path, order)
    journal_dir = tmp_path_from_runtime(runtime) / "order_transactions"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = {"transaction_id": "TXN-2026-000002", "state": "RUNNING", "order_id": "ORD-2026-000001", "affected_files": [str(order_path)], "backup_targets": [str(order_path)], "created_at": "2026-05-23T00:00:00+00:00", "error_message": ""}
    (journal_dir / "TXN-2026-000002.json").write_text(json.dumps(journal), encoding="utf-8")
    recovered = build_order_service(runtime).recover_incomplete_transactions()
    restored = runtime["json_service"].read_json(order_path, {})
    assert recovered[0]["state"] == "ROLLED_BACK"
    assert restored["status"] == "CONFIRMED"


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
    service.enqueue_message("buyer@example.com", "Subject", "Body", "ledger_reminder")
    service.send_message = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("smtp down"))  # type: ignore[method-assign]
    processed = service.process_queue()
    queue = JsonServiceStub().read_json(queue_path, {"messages": []})
    assert processed == 0
    assert queue["messages"][0]["status"] == "retry"
