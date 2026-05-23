from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from services.agreement_service import AgreementService
from services.delivery_service import DeliveryService
from services.event_dispatcher import EventDispatcher
from services.file_lock_service import FileLockService
from services.id_allocator_service import IdAllocatorService
from services.order_state_service import OrderStateService
from services.order_transaction_service import OrderTransactionService
from services.order_validation_service import OrderValidationService
from services.procurement_matching_service import ProcurementMatchingService
from services.procurement_transaction_service import ProcurementTransactionService
from services.rollback_service import RollbackService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.startup_recovery_service import StartupRecoveryService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import AuditStub, GmailStub, LoggingStub


class AgreementSettlementStub:
    def confirm_settlement(self, agreement, amount, actor):
        agreement["status"] = "CLOSED"
        agreement["settled_by"] = actor
        agreement["settled_amount"] = amount
        return agreement


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
    return {
        "json_service": json_service,
        "logging_service": logging_service,
        "file_lock_service": file_lock_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "drive": drive,
        "event_dispatcher": event_dispatcher,
        "rollback_service": rollback_service,
    }


def seed_inventory(runtime: dict, manufacturer_code: str, product_code="PRD101", quantity=100, city="Pune"):
    path = runtime["drive"].get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"
    runtime["json_service"].write_json(
        path,
        {
            "schema_version": "1.0",
            "manufacturer_code": manufacturer_code,
            "items": [
                {
                    "product_code": product_code,
                    "product_name": "Wheat",
                    "quantity": quantity,
                    "reserved_quantity": 0,
                    "city": city,
                }
            ],
        },
    )
    return path


def seed_agreements(runtime: dict, manufacturer_code: str):
    path = runtime["drive"].get_manufacturer_paths(manufacturer_code).shared_zone / "agreements.json"
    runtime["json_service"].write_json(
        path,
        {"schema_version": "1.0", "manufacturer_code": manufacturer_code, "agreements": []},
    )
    return path


def seed_procurement_request(runtime: dict, owner_code: str, request_id="REQ-2026-000001", product_code="PRD101", qty=20, city="Pune", requested_by: str | None = None):
    path = runtime["drive"].get_manufacturer_paths(owner_code).shared_zone / "procurement.json"
    runtime["json_service"].write_json(
        path,
        {
            "schema_version": "1.0",
            "manufacturer_code": owner_code,
            "requests": [
                {
                    "request_id": request_id,
                    "product_id": product_code,
                    "required_qty": qty,
                    "requested_by": requested_by or owner_code,
                    "city": city,
                    "status": "OPEN",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    return path


def seed_order(runtime: dict, manufacturer_code: str, status="DISPATCH_READY", reserved_qty=10, with_agreement=True):
    month_key = datetime.now(UTC).strftime("%Y-%m")
    order_id = "ORD-2026-000001"
    agreement_id = "AGR-2026-000001" if with_agreement else ""
    inventory_path = seed_inventory(runtime, manufacturer_code, quantity=50)
    inventory = runtime["json_service"].read_json(inventory_path, {})
    inventory["items"][0]["reserved_quantity"] = reserved_qty
    runtime["json_service"].write_json(inventory_path, inventory)
    if with_agreement:
        agreements_path = seed_agreements(runtime, manufacturer_code)
        runtime["json_service"].write_json(
            agreements_path,
            {
                "schema_version": "1.0",
                "manufacturer_code": manufacturer_code,
                "agreements": [
                    {
                        "schema_version": "1.0",
                        "agreement_id": agreement_id,
                        "status": "ADVANCE_PENDING",
                        "order_id": order_id,
                    }
                ],
            },
        )
    order = {
        "schema_version": "1.0",
        "order_id": order_id,
        "client_id": "CLIENT-2026-000001",
        "client_email": "buyer@example.com",
        "manufacturer_id": manufacturer_code,
        "items": [{"product_id": "PRD101", "product_name": "Wheat", "qty": reserved_qty, "mrp": 145.0}],
        "status": status,
        "created_at": datetime.now(UTC).date().isoformat(),
        "status_history": [],
        "agreement_id": agreement_id if with_agreement else "",
    }
    order_path = runtime["drive"].resolve_orders_month_dir(manufacturer_code, month_key) / f"{order_id}.json"
    runtime["json_service"].write_json(order_path, order)
    runtime["json_service"].write_json(
        runtime["drive"].get_manufacturer_paths(manufacturer_code).private_zone / "client_orders" / f"{order_id}.json",
        order,
    )
    return order_path


def build_order_service(runtime: dict, gmail_service=None, event_dispatcher=None, agreement_service=None, delivery_service=None, safe_write=None, order_state_service=None):
    gmail = gmail_service or GmailStub()
    agreement = agreement_service or AgreementService(id_allocator_service=runtime["allocator"])
    delivery = delivery_service or DeliveryService(gmail_service=gmail, audit_service=AuditStub(), id_allocator_service=runtime["allocator"])
    return OrderTransactionService(
        drive_service=runtime["drive"],
        safe_drive_write_service=safe_write or runtime["safe_write"],
        rollback_service=RollbackService(safe_write or runtime["safe_write"], runtime["logging_service"]),
        order_state_service=order_state_service or OrderStateService(audit_service=AuditStub()),
        agreement_service=agreement,
        agreement_settlement_service=AgreementSettlementStub(),
        delivery_service=delivery,
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=runtime["logging_service"],
        event_dispatcher=event_dispatcher or runtime["event_dispatcher"],
        transactions_root=tmp_path_from_runtime(runtime) / "order_transactions",
        id_allocator_service=runtime["allocator"],
    )


def build_procurement_service(runtime: dict, gmail_service=None, event_dispatcher=None, agreement_service=None, safe_write=None):
    gmail = gmail_service or GmailStub()
    agreement = agreement_service or AgreementService(id_allocator_service=runtime["allocator"])
    return ProcurementTransactionService(
        drive_service=runtime["drive"],
        agreement_service=agreement,
        safe_drive_write_service=safe_write or runtime["safe_write"],
        rollback_service=RollbackService(safe_write or runtime["safe_write"], runtime["logging_service"]),
        order_validation_service=OrderValidationService(runtime["drive"], safe_write or runtime["safe_write"], runtime["allocator"]),
        procurement_matching_service=ProcurementMatchingService(),
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=runtime["logging_service"],
        transactions_root=tmp_path_from_runtime(runtime) / "transactions",
        event_dispatcher=event_dispatcher or runtime["event_dispatcher"],
        id_allocator_service=runtime["allocator"],
    )


def build_startup_recovery(runtime: dict, procurement_service, order_service):
    return StartupRecoveryService(procurement_service, order_service, runtime["file_lock_service"])


def current_user(manufacturer_code="MANU101", email="user@example.com"):
    return SimpleNamespace(manufacturer_code=manufacturer_code, email=email)


def tmp_path_from_runtime(runtime: dict) -> Path:
    return runtime["allocator"].counters_path.parent
