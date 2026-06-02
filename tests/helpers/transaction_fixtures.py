from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from services.client_service import ClientService
from services.delivery_service import DeliveryService
from services.domain_paths_service import DomainPathsService
from services.dual_inventory_service import DualInventoryService
from services.encryption_service import EncryptionService
from services.event_dispatcher import EventDispatcher
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.ledger_service import LedgerService
from services.notification_center_service import NotificationCenterService
from services.order_state_service import OrderStateService
from services.order_transaction_service import OrderTransactionService
from services.pricing_service import PricingService
from services.procurement_transaction_service import ProcurementTransactionService
from services.rollback_service import RollbackService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.startup_recovery_service import StartupRecoveryService
from services.trade_confirmation_service import TradeConfirmationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import AuditStub, GmailStub, LoggingStub


def build_runtime(tmp_path: Path):
    json_service = JsonServiceStub()
    logging_service = LoggingStub()
    file_lock_service = FileLockService()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=file_lock_service,
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=logging_service,
        version_history_root=tmp_path / "version_history",
    )
    allocator = IdAllocatorService(tmp_path / "id_counters.json", file_lock_service)
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    event_dispatcher = EventDispatcher(tmp_path / "events", id_allocator_service=allocator)
    rollback_service = RollbackService(safe_write, logging_service)
    domain_paths = DomainPathsService(drive)
    governance = GovernanceService(tmp_path / "governance", safe_write)
    governance.ensure_files()
    pricing = PricingService({"admin_profit_share_percent": 50, "manufacturer_profit_share_percent": 50, "mahajan_transaction_fee_percent": 1})
    client_service = ClientService(
        drive_service=drive,
        gmail_service=GmailStub(),
        encryption_service=EncryptionService(secret_seed="test-seed"),
        safe_drive_write_service=safe_write,
        id_allocator_service=allocator,
        logging_service=logging_service,
    )
    return {
        "json_service": json_service,
        "logging_service": logging_service,
        "file_lock_service": file_lock_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "drive": drive,
        "event_dispatcher": event_dispatcher,
        "rollback_service": rollback_service,
        "domain_paths": domain_paths,
        "governance": governance,
        "pricing": pricing,
        "client_service": client_service,
    }


def seed_inventory(runtime: dict, manufacturer_code: str, product_id: str = "PRD-2026-000001", self_qty: int = 100, mandi_qty: int = 50):
    service = DualInventoryService(runtime["safe_write"], runtime["json_service"], runtime["domain_paths"])
    service.upsert_inventory_item(manufacturer_code, product_id=product_id, product_name="Rice", unit="kg", self_available_qty=self_qty, mandi_available_qty=mandi_qty)
    return runtime["domain_paths"].inventory_path(manufacturer_code)


def seed_rfq_doc(runtime: dict, manufacturer_code: str):
    path = runtime["domain_paths"].rfq_path(manufacturer_code)
    runtime["json_service"].write_json(path, {"schema_version": "2.0", "rfqs": [], "responses": []})
    return path


def seed_order(runtime: dict, manufacturer_code: str, status: str = "CONFIRMED", reserved_qty: int = 10):
    month_key = datetime.now(UTC).strftime("%Y-%m")
    order_id = "ORD-2026-000001"
    seed_inventory(runtime, manufacturer_code, self_qty=50, mandi_qty=10)
    inventory_path = runtime["domain_paths"].inventory_path(manufacturer_code)
    inventory = runtime["json_service"].read_json(inventory_path, {})
    inventory["items"][0]["self_inventory"]["reserved_qty"] = reserved_qty
    runtime["json_service"].write_json(inventory_path, inventory)
    order = {
        "schema_version": "2.0",
        "order_id": order_id,
        "client_id": "CLIENT101",
        "client_email": "buyer@example.com",
        "manufacturer_id": manufacturer_code,
        "primary_manufacturer_id": manufacturer_code,
        "items": [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": reserved_qty, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        "payment_proposal": {"payment_modes": ["cash"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "30% upfront"},
        "status": status,
        "status_history": [],
        "created_at": datetime.now(UTC).date().isoformat(),
    }
    order_path = runtime["drive"].resolve_orders_month_dir(manufacturer_code, month_key) / f"{order_id}.json"
    runtime["json_service"].write_json(order_path, order)
    runtime["json_service"].write_json(runtime["domain_paths"].client_order_path(manufacturer_code, order_id), order)
    return order_path


def build_procurement_service(runtime: dict, gmail_service=None, event_dispatcher=None, safe_write=None):
    gmail = gmail_service or GmailStub()
    trade_confirmation_service = TradeConfirmationService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    ledger_service = LedgerService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    notification_center_service = NotificationCenterService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    dual_inventory_service = DualInventoryService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["domain_paths"])
    return ProcurementTransactionService(
        drive_service=runtime["drive"],
        safe_drive_write_service=safe_write or runtime["safe_write"],
        rollback_service=RollbackService(safe_write or runtime["safe_write"], runtime["logging_service"]),
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=runtime["logging_service"],
        transactions_root=tmp_path_from_runtime(runtime) / "transactions",
        event_dispatcher=event_dispatcher or runtime["event_dispatcher"],
        id_allocator_service=runtime["allocator"],
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_center_service,
        domain_paths_service=runtime["domain_paths"],
        governance_service=runtime["governance"],
        pricing_service=runtime["pricing"],
    )


def build_order_service(runtime: dict, gmail_service=None, event_dispatcher=None, delivery_service=None, safe_write=None, order_state_service=None, procurement_service=None):
    gmail = gmail_service or GmailStub()
    trade_confirmation_service = TradeConfirmationService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    ledger_service = LedgerService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    notification_center_service = NotificationCenterService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    dual_inventory_service = DualInventoryService(safe_write or runtime["safe_write"], runtime["json_service"], runtime["domain_paths"])
    procurement = procurement_service or build_procurement_service(runtime, gmail_service=gmail, event_dispatcher=event_dispatcher, safe_write=safe_write)
    delivery = delivery_service or DeliveryService(gmail_service=gmail, audit_service=AuditStub(), id_allocator_service=runtime["allocator"])
    return OrderTransactionService(
        drive_service=runtime["drive"],
        safe_drive_write_service=safe_write or runtime["safe_write"],
        rollback_service=RollbackService(safe_write or runtime["safe_write"], runtime["logging_service"]),
        order_state_service=order_state_service or OrderStateService(audit_service=AuditStub()),
        delivery_service=delivery,
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=runtime["logging_service"],
        event_dispatcher=event_dispatcher or runtime["event_dispatcher"],
        transactions_root=tmp_path_from_runtime(runtime) / "order_transactions",
        id_allocator_service=runtime["allocator"],
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_center_service,
        domain_paths_service=runtime["domain_paths"],
        procurement_transaction_service=procurement,
        client_service=runtime["client_service"],
    )


def build_startup_recovery(runtime: dict, procurement_service, order_service):
    return StartupRecoveryService(procurement_service, order_service, runtime["file_lock_service"])


def current_user(manufacturer_code="MANU101", email="user@example.com", role="manufacturer"):
    return SimpleNamespace(manufacturer_code=manufacturer_code, email=email, role=role)


def tmp_path_from_runtime(runtime: dict) -> Path:
    return runtime["allocator"].counters_path.parent
