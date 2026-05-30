from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.access_portal_service import AccessPortalService
from services.action_center_service import ActionCenterService
from services.client_service import ClientService
from services.delivery_service import DeliveryService
from services.domain_paths_service import DomainPathsService
from services.dual_inventory_service import DualInventoryService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.ledger_service import LedgerService
from services.notification_center_service import NotificationCenterService
from services.order_state_service import OrderStateService
from services.order_transaction_service import OrderTransactionService
from services.pricing_service import PricingService
from services.procurement_transaction_service import ProcurementTransactionService
from services.product_catalog_service import ProductCatalogService
from services.public_buyer_service import PublicBuyerService
from services.public_cart_service import PublicCartService
from services.public_order_service import PublicOrderService
from services.query.inventory_query_service import InventoryQueryService
from services.query.order_query_service import OrderQueryService
from services.query.procurement_query_service import ProcurementQueryService
from services.rollback_service import RollbackService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.trade_confirmation_service import TradeConfirmationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import AuditStub, GmailStub, LoggingStub


class PilotIdAllocator:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    def allocate(self, domain: str) -> str:
        self.counters[domain] = self.counters.get(domain, 0) + 1
        return f"PILOT_TEST_{domain.upper()}_{self.counters[domain]:04d}"


def _build_stack(root: Path) -> dict[str, Any]:
    json_service = JsonServiceStub()
    logging_service = LoggingStub()
    file_lock_service = FileLockService()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=file_lock_service,
        schema_validation_service=SchemaValidationService(),
        backups_root=root / "backups",
        logging_service=logging_service,
        version_history_root=root / "history",
    )
    allocator = PilotIdAllocator()
    drive = DriveStub(root / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    domain_paths = DomainPathsService(drive)
    governance = GovernanceService(root / "governance", safe_write)
    governance.ensure_files()
    gmail = GmailStub()
    pricing = PricingService(
        {
            "admin_profit_share_percent": 50,
            "manufacturer_profit_share_percent": 50,
            "platform_fee_on_admin_commission": {"basic": 10, "premium": 5, "premium_plus": 1},
        }
    )
    client_service = ClientService(
        drive_service=drive,
        gmail_service=gmail,
        encryption_service=type("EncryptionStub", (), {"encrypt": lambda self, value: f"PILOT_TEST_TOKEN::{value}"})(),
        safe_drive_write_service=safe_write,
        id_allocator_service=allocator,
        logging_service=logging_service,
    )
    notification_service = NotificationCenterService(
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        domain_paths_service=domain_paths,
        public_buyers_root=root / "public_buyers",
    )
    product_service = ProductCatalogService(
        governance_service=governance,
        id_allocator_service=allocator,
        notification_center_service=notification_service,
        gmail_service=gmail,
        admin_email="pilot_test_superadmin@example.com",
        pricing_service=pricing,
    )
    dual_inventory_service = DualInventoryService(safe_write, json_service, domain_paths)
    trade_confirmation_service = TradeConfirmationService(safe_write, json_service, allocator, domain_paths)
    ledger_service = LedgerService(safe_write, json_service, allocator, domain_paths)
    rollback_service = RollbackService(safe_write, logging_service)
    procurement_service = ProcurementTransactionService(
        drive_service=drive,
        safe_drive_write_service=safe_write,
        rollback_service=rollback_service,
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=logging_service,
        transactions_root=root / "transactions",
        event_dispatcher=type("EventStub", (), {"emit": lambda self, *_args, **_kwargs: None})(),
        id_allocator_service=allocator,
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_service,
        domain_paths_service=domain_paths,
    )
    order_service = OrderTransactionService(
        drive_service=drive,
        safe_drive_write_service=safe_write,
        rollback_service=rollback_service,
        order_state_service=OrderStateService(audit_service=AuditStub()),
        delivery_service=DeliveryService(gmail_service=gmail, audit_service=AuditStub(), id_allocator_service=allocator),
        gmail_service=gmail,
        audit_service=AuditStub(),
        logging_service=logging_service,
        event_dispatcher=type("EventStub", (), {"emit": lambda self, *_args, **_kwargs: None})(),
        transactions_root=root / "order_transactions",
        id_allocator_service=allocator,
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_service,
        domain_paths_service=domain_paths,
        pricing_service=pricing,
        procurement_transaction_service=procurement_service,
    )
    public_buyer_service = PublicBuyerService(root / "public_buyers", safe_write, json_service, allocator)
    public_cart_service = PublicCartService(public_buyer_service, product_service, safe_write, json_service, allocator)
    public_order_service = PublicOrderService(
        public_orders_root=root / "public_orders",
        public_payments_root=root / "public_payments",
        public_buyer_service=public_buyer_service,
        public_cart_service=public_cart_service,
        product_catalog_service=product_service,
        dual_inventory_service=dual_inventory_service,
        notification_center_service=notification_service,
        gmail_service=gmail,
        governance_service=governance,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        pricing_service=pricing,
        config={"mode": "UPI_MANUAL", "instructions": "PILOT_TEST full upfront payment required."},
    )
    order_query_service = OrderQueryService(drive, json_service, domain_paths)
    inventory_query_service = InventoryQueryService(drive, json_service, domain_paths)
    procurement_query_service = ProcurementQueryService(drive, json_service)
    action_center_service = ActionCenterService(
        governance_service=governance,
        gmail_service=gmail,
        notification_center_service=notification_service,
        ledger_service=ledger_service,
        order_query_service=order_query_service,
        procurement_query_service=procurement_query_service,
        dual_inventory_service=dual_inventory_service,
        public_order_service=public_order_service,
    )
    access_service = AccessPortalService(
        governance_root=root / "governance",
        safe_drive_write_service=safe_write,
        governance_service=governance,
        client_service=client_service,
        worker_service=type("WorkerStub", (), {"get_worker_by_email": lambda self, _email: None, "upsert_worker": lambda self, **_kwargs: None})(),
        public_buyer_service=public_buyer_service,
        drive_service=drive,
        security_service=type("SecurityStub", (), {"get_admin_email": lambda self: "pilot_test_superadmin@example.com"})(),
        json_service=json_service,
    )
    return {
        "root": root,
        "json_service": json_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "drive": drive,
        "domain_paths": domain_paths,
        "governance": governance,
        "gmail": gmail,
        "pricing": pricing,
        "client_service": client_service,
        "notification_service": notification_service,
        "product_service": product_service,
        "dual_inventory_service": dual_inventory_service,
        "trade_confirmation_service": trade_confirmation_service,
        "ledger_service": ledger_service,
        "procurement_service": procurement_service,
        "order_service": order_service,
        "public_buyer_service": public_buyer_service,
        "public_cart_service": public_cart_service,
        "public_order_service": public_order_service,
        "order_query_service": order_query_service,
        "inventory_query_service": inventory_query_service,
        "procurement_query_service": procurement_query_service,
        "action_center_service": action_center_service,
        "access_service": access_service,
    }


def seed_pilot_flow(root: Path, *, safe_mode: bool = True) -> dict[str, Any]:
    if not safe_mode:
        raise ValueError("Pilot seed refuses to run without safe_mode=True.")
    stack = _build_stack(root)
    governance = stack["governance"]
    drive = stack["drive"]
    product_service = stack["product_service"]
    client_service = stack["client_service"]
    dual_inventory_service = stack["dual_inventory_service"]
    order_service = stack["order_service"]
    procurement_service = stack["procurement_service"]
    public_buyer_service = stack["public_buyer_service"]
    public_cart_service = stack["public_cart_service"]
    public_order_service = stack["public_order_service"]
    ledger_service = stack["ledger_service"]
    notification_service = stack["notification_service"]
    action_center_service = stack["action_center_service"]

    manufacturers = [
        {
            "manufacturer_code": "PILOT_TEST_MANU001",
            "manufacturer_name": "PILOT_TEST Alpha Foods",
            "business_name": "PILOT_TEST Alpha Foods",
            "owner_email": "pilot_test_alpha_owner@example.com",
            "status": "ACTIVE",
            "subscription_plan": "basic",
            "product_categories": ["Staples", "Grains"],
            "banking": {"account_holder_name": "PILOT_TEST Alpha Foods", "upi_id": "pilotalpha@upi"},
        },
        {
            "manufacturer_code": "PILOT_TEST_MANU002",
            "manufacturer_name": "PILOT_TEST Beta Agro",
            "business_name": "PILOT_TEST Beta Agro",
            "owner_email": "pilot_test_beta_owner@example.com",
            "status": "ACTIVE",
            "subscription_plan": "premium",
            "product_categories": ["Staples", "Pulses"],
            "banking": {"account_holder_name": "PILOT_TEST Beta Agro", "upi_id": "pilotbeta@upi"},
        },
    ]
    for manufacturer in manufacturers:
        drive.initialize_manufacturer_workspace(
            manufacturer["manufacturer_code"],
            manufacturer["business_name"],
            owner_email=manufacturer["owner_email"],
            city="Pune",
        )
        governance.register_manufacturer(manufacturer)

    products = []
    for payload in [
        {
            "product_id": "PILOT_TEST_PRODUCT_0001",
            "name": "PILOT_TEST Rice 25kg",
            "category": "Staples",
            "unit": "bag",
            "created_by": "PILOT_TEST_MANU001",
            "created_by_manufacturer_id": "PILOT_TEST_MANU001",
            "created_by_email": "pilot_test_alpha_owner@example.com",
            "public_seller_manufacturer_id": "PILOT_TEST_MANU001",
            "status": "ACTIVE",
            "visible": True,
            "approved_visibility": "PRIVATE_CLIENT",
            "available_for_public_sale": False,
            "available_for_mandi_network": True,
            "mandi_price": 38.0,
            "client_price": 44.0,
            "marketplace_price": 49.0,
            "mrp": 44.0,
            "approved_mandi_price": 38.0,
            "approved_client_price": 44.0,
            "approved_marketplace_price": 49.0,
        },
        {
            "product_id": "PILOT_TEST_PRODUCT_0002",
            "name": "PILOT_TEST Wheat 25kg",
            "category": "Staples",
            "unit": "bag",
            "created_by": "PILOT_TEST_MANU001",
            "created_by_manufacturer_id": "PILOT_TEST_MANU001",
            "created_by_email": "pilot_test_alpha_owner@example.com",
            "public_seller_manufacturer_id": "PILOT_TEST_MANU001",
            "status": "ACTIVE",
            "visible": True,
            "approved_visibility": "PUBLIC",
            "available_for_public_sale": True,
            "available_for_mandi_network": True,
            "mandi_price": 30.0,
            "client_price": 36.0,
            "marketplace_price": 41.0,
            "mrp": 36.0,
            "approved_mandi_price": 30.0,
            "approved_client_price": 36.0,
            "approved_marketplace_price": 41.0,
        },
        {
            "product_id": "PILOT_TEST_PRODUCT_0003",
            "name": "PILOT_TEST Toor Dal 10kg",
            "category": "Pulses",
            "unit": "bag",
            "created_by": "PILOT_TEST_MANU002",
            "created_by_manufacturer_id": "PILOT_TEST_MANU002",
            "created_by_email": "pilot_test_beta_owner@example.com",
            "public_seller_manufacturer_id": "PILOT_TEST_MANU002",
            "status": "ACTIVE",
            "visible": True,
            "approved_visibility": "MANDI_NETWORK",
            "available_for_public_sale": False,
            "available_for_mandi_network": True,
            "mandi_price": 42.0,
            "client_price": 48.0,
            "marketplace_price": 53.0,
            "mrp": 48.0,
            "approved_mandi_price": 42.0,
            "approved_client_price": 48.0,
            "approved_marketplace_price": 53.0,
        },
    ]:
        governance.upsert_product({"schema_version": "1.0", **payload})
        products.append(payload["product_id"])

    dual_inventory_service.upsert_inventory_item("PILOT_TEST_MANU001", product_id="PILOT_TEST_PRODUCT_0001", product_name="PILOT_TEST Rice 25kg", unit="bag", self_available_qty=120, mandi_available_qty=15)
    dual_inventory_service.upsert_inventory_item("PILOT_TEST_MANU001", product_id="PILOT_TEST_PRODUCT_0002", product_name="PILOT_TEST Wheat 25kg", unit="bag", self_available_qty=85, mandi_available_qty=20)
    dual_inventory_service.upsert_inventory_item("PILOT_TEST_MANU002", product_id="PILOT_TEST_PRODUCT_0003", product_name="PILOT_TEST Toor Dal 10kg", unit="bag", self_available_qty=45, mandi_available_qty=150)

    clients = [
        client_service.create_client(
            "PILOT_TEST_MANU001",
            {
                "client_id": "PILOT_TEST_CLIENT_0001",
                "business_name": "PILOT_TEST Shree Retail",
                "owner_name": "PILOT_TEST Amit Kumar",
                "email": "pilot_test_client1@example.com",
                "mobile": "9999990001",
                "status": "ACTIVE",
                "invite_status": "ACCEPTED",
                "address": {"line1": "PILOT_TEST Lane 1", "city": "Pune", "state": "Maharashtra"},
            },
        ),
        client_service.create_client(
            "PILOT_TEST_MANU002",
            {
                "client_id": "PILOT_TEST_CLIENT_0002",
                "business_name": "PILOT_TEST Metro Store",
                "owner_name": "PILOT_TEST Neha Singh",
                "email": "pilot_test_client2@example.com",
                "mobile": "9999990002",
                "status": "ACTIVE",
                "invite_status": "ACCEPTED",
                "address": {"line1": "PILOT_TEST Lane 2", "city": "Pune", "state": "Maharashtra"},
            },
        ),
    ]

    private_order = order_service.create_order(
        "PILOT_TEST_MANU001",
        clients[0],
        [
            {"product_id": "PILOT_TEST_PRODUCT_0001", "product_name": "PILOT_TEST Rice 25kg", "qty": 10, "unit": "bag", "client_price": 44.0, "mrp": 44.0, "mandi_price": 38.0},
            {"product_id": "PILOT_TEST_PRODUCT_0002", "product_name": "PILOT_TEST Wheat 25kg", "qty": 5, "unit": "bag", "client_price": 36.0, "mrp": 36.0, "mandi_price": 30.0},
        ],
        {"payment_modes": ["cash", "upi"], "upfront_percentage": 30, "ledger_days": 14, "freestyle_note": "PILOT_TEST private proposal"},
    )
    confirmed_private_order = order_service.confirm_order(
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU001", "email": "pilot_test_alpha_owner@example.com", "role": "manufacturer"})(),
        private_order["order_id"],
    )

    shortage_order = order_service.create_order(
        "PILOT_TEST_MANU001",
        clients[0],
        [
            {"product_id": "PILOT_TEST_PRODUCT_0003", "product_name": "PILOT_TEST Toor Dal 10kg", "qty": 60, "unit": "bag", "client_price": 48.0, "mrp": 48.0, "mandi_price": 42.0},
        ],
        {"payment_modes": ["cash"], "upfront_percentage": 20, "ledger_days": 10, "freestyle_note": "PILOT_TEST shortage scenario"},
    )
    rfq_id = shortage_order["rfq_id"]
    response = procurement_service.respond_to_rfq(
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU002", "email": "pilot_test_beta_owner@example.com", "role": "manufacturer"})(),
        "PILOT_TEST_MANU001",
        rfq_id,
        [{"product_id": "PILOT_TEST_PRODUCT_0003", "qty": 60, "unit": "bag", "offered_unit_price": 42.0}],
        {"upfront_percentage": 40, "ledger_days": 15, "freestyle_note": "PILOT_TEST can supply today"},
    )
    procurement_service.accept_rfq_response(
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU001", "email": "pilot_test_alpha_owner@example.com", "role": "manufacturer"})(),
        rfq_id,
        response["response_id"],
    )

    public_buyer = public_buyer_service.register_or_get(email="pilot_test_public@example.com", full_name="PILOT_TEST Public Buyer")
    public_cart_service.add_item(public_buyer["public_buyer_id"], product_id="PILOT_TEST_PRODUCT_0002", qty=2)
    public_order = public_order_service.create_order_from_cart(public_buyer["public_buyer_id"])
    public_buyer_actions_before_payment = action_center_service.get_actions(
        type("User", (), {"manufacturer_code": None, "email": "pilot_test_public@example.com", "role": "public_buyer"})()
    )
    public_order_service.submit_payment_reference(public_order["public_order_id"], public_buyer["public_buyer_id"], payment_reference="PILOT_TEST_UTR_0001")
    manufacturer_actions_before_public_verify = action_center_service.get_actions(
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU001", "email": "pilot_test_alpha_owner@example.com", "role": "manufacturer"})()
    )
    paid_public_order = public_order_service.verify_payment(
        public_order["public_order_id"],
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU001", "email": "pilot_test_alpha_owner@example.com", "role": "manufacturer"})(),
        approved=True,
    )

    notification = notification_service.create_notification(
        "PILOT_TEST_MANU001",
        user_id="PILOT_TEST_MANU001",
        notification_type="PILOT_TEST_ALERT",
        priority="HIGH",
        title="PILOT_TEST notification",
        message="PILOT_TEST seeded notification.",
        source_type="PILOT_TEST",
        source_id="PILOT_TEST_SOURCE_0001",
    )

    manufacturer_actions = action_center_service.get_actions(
        type("User", (), {"manufacturer_code": "PILOT_TEST_MANU001", "email": "pilot_test_alpha_owner@example.com", "role": "manufacturer"})()
    )
    public_buyer_actions = action_center_service.get_actions(
        type("User", (), {"manufacturer_code": None, "email": "pilot_test_public@example.com", "role": "public_buyer"})()
    )
    superadmin_actions = action_center_service.get_actions(type("User", (), {"role": "platform_admin", "email": "pilot_test_superadmin@example.com"})())

    summary = {
        "safe_mode": safe_mode,
        "root": str(root),
        "manufacturers": [item["manufacturer_code"] for item in manufacturers],
        "clients": [item["client_id"] for item in clients],
        "products": products,
        "private_order_id": confirmed_private_order["order_id"],
        "rfq_id": rfq_id,
        "rfq_response_id": response["response_id"],
        "public_order_id": paid_public_order["public_order_id"],
        "notification_id": notification["notification_id"],
        "manufacturer_actions_before_public_verify": manufacturer_actions_before_public_verify,
        "manufacturer_actions": manufacturer_actions,
        "public_buyer_actions_before_payment": public_buyer_actions_before_payment,
        "public_buyer_actions": public_buyer_actions,
        "superadmin_actions": superadmin_actions,
        "gmail_messages": stack["gmail"].sent,
        "private_ledgers": ledger_service.list_ledgers("PILOT_TEST_MANU001"),
        "shared_inventory_projection": stack["inventory_query_service"].list_inventory_snapshot("PILOT_TEST_MANU001"),
        "private_order_projection": stack["json_service"].read_json(
            stack["domain_paths"].shared_client_order_projection_path("PILOT_TEST_MANU001", confirmed_private_order["created_at"][:7], confirmed_private_order["order_id"]),
            {},
        ),
    }
    (root / "pilot_seed_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"stack": stack, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a safe isolated MandiTrade pilot flow.")
    parser.add_argument("--output-dir", default="runtime/pilot_seed", help="Target folder for isolated pilot seed data.")
    parser.add_argument("--force-safe", action="store_true", help="Allow seeding only into an isolated safe folder.")
    args = parser.parse_args()

    safe_env = os.environ.get("PILOT_TEST_MODE", "").strip() == "1"
    output_dir = Path(args.output_dir).resolve()
    if not args.force_safe and not safe_env:
        raise SystemExit("Refusing to seed pilot flow. Set PILOT_TEST_MODE=1 or pass --force-safe.")
    result = seed_pilot_flow(output_dir, safe_mode=True)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
