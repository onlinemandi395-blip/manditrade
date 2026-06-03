from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from bootstrap.route_registry import can_access_route
from services.dispute_service import DisputeService
from services.event_notification_service import EventNotificationService
from services.invoice_service import InvoiceService
from services.notification_center_service import NotificationCenterService
from services.product_catalog_service import ProductCatalogService
from services.public_buyer_service import PublicBuyerService
from services.public_cart_service import PublicCartService
from services.public_order_service import PublicOrderService
from services.settlement_service import SettlementService
from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime


class _NotificationStub:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create_notification(self, owner_id, **kwargs):
        row = {"owner_id": owner_id, **kwargs}
        self.rows.append(row)
        return row

    def create_public_notification(self, owner_id, **kwargs):
        row = {"owner_id": owner_id, **kwargs}
        self.rows.append(row)
        return row


class _GmailStub:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def enqueue_message(self, recipient_email, subject, body, event_type, deep_link="", metadata=None):
        self.messages.append(
            {
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "event_type": event_type,
                "deep_link": deep_link,
                "metadata": metadata or {},
            }
        )


def _build_finance_stack(tmp_path: Path) -> dict:
    runtime = build_runtime(tmp_path)
    governance = runtime["governance"]
    notifications = _NotificationStub()
    gmail = _GmailStub()
    public_buyer_service = PublicBuyerService(tmp_path / "public_buyers", runtime["safe_write"], runtime["json_service"], runtime["allocator"])
    event_notification_service = EventNotificationService(
        notification_center_service=notifications,
        gmail_service=gmail,
        governance_service=governance,
        public_buyer_service=public_buyer_service,
        notification_rules={},
    )
    settlement_service = SettlementService(
        governance_service=governance,
        id_allocator_service=runtime["allocator"],
        safe_drive_write_service=runtime["safe_write"],
        json_service=runtime["json_service"],
        runtime_root=tmp_path / "runtime",
        event_notification_service=event_notification_service,
    )
    invoice_service = InvoiceService(
        runtime_root=tmp_path / "runtime",
        safe_drive_write_service=runtime["safe_write"],
        id_allocator_service=runtime["allocator"],
        json_service=runtime["json_service"],
        event_notification_service=event_notification_service,
    )
    dispute_service = DisputeService(
        governance_service=governance,
        id_allocator_service=runtime["allocator"],
        settlement_service=settlement_service,
        event_notification_service=event_notification_service,
    )
    product_service = ProductCatalogService(
        governance_service=governance,
        id_allocator_service=runtime["allocator"],
        notification_center_service=NotificationCenterService(
            safe_drive_write_service=runtime["safe_write"],
            json_service=runtime["json_service"],
            id_allocator_service=runtime["allocator"],
            domain_paths_service=runtime["domain_paths"],
            public_buyers_root=tmp_path / "public_buyers",
        ),
        gmail_service=gmail,
        admin_email="admin@example.com",
    )
    public_cart_service = PublicCartService(
        public_buyer_service=public_buyer_service,
        product_catalog_service=product_service,
        safe_drive_write_service=runtime["safe_write"],
        json_service=runtime["json_service"],
        id_allocator_service=runtime["allocator"],
    )
    public_order_service = PublicOrderService(
        public_orders_root=tmp_path / "public_orders",
        public_payments_root=tmp_path / "public_payments",
        public_buyer_service=public_buyer_service,
        public_cart_service=public_cart_service,
        product_catalog_service=product_service,
        dual_inventory_service=SimpleNamespace(
            reserve_self_inventory=lambda *_args, **_kwargs: None,
            finalize_reserved=lambda *_args, **_kwargs: None,
        ),
        notification_center_service=notifications,
        gmail_service=gmail,
        governance_service=governance,
        safe_drive_write_service=runtime["safe_write"],
        json_service=runtime["json_service"],
        id_allocator_service=runtime["allocator"],
        pricing_service=runtime["pricing"],
        config={"mode": "UPI_MANUAL"},
        event_notification_service=event_notification_service,
        settlement_service=settlement_service,
        invoice_service=invoice_service,
    )
    procurement_service = build_procurement_service(runtime)
    procurement_service.settlement_service = settlement_service
    procurement_service.invoice_service = invoice_service
    procurement_service.event_notification_service = event_notification_service
    return {
        **runtime,
        "governance": governance,
        "settlement_service": settlement_service,
        "invoice_service": invoice_service,
        "dispute_service": dispute_service,
        "notifications": notifications,
        "gmail": gmail,
        "public_buyer_service": public_buyer_service,
        "public_cart_service": public_cart_service,
        "public_order_service": public_order_service,
        "product_service": product_service,
        "procurement_service": procurement_service,
    }


def _seed_public_product(stack: dict) -> None:
    stack["governance"].register_manufacturer(
        {
            "manufacturer_code": "MANU101",
            "manufacturer_id": "MANU101",
            "business_name": "Seller One",
            "owner_email": "seller@example.com",
            "status": "ACTIVE",
            "banking": {"upi_id": "seller@upi", "account_holder_name": "Seller One"},
        }
    )
    stack["governance"].upsert_product(
        {
            "product_id": "PRD001",
            "name": "Rice",
            "status": "ACTIVE",
            "visible": True,
            "approved_visibility": "PUBLIC",
            "available_for_public_sale": True,
            "public_seller_manufacturer_id": "MANU101",
            "marketplace_price": 500,
            "approved_marketplace_price": 500,
            "mandi_price": 420,
            "approved_mandi_price": 420,
            "unit": "bag",
            "tax_profile": {"gst_number": "27ABCDE1234F1Z5", "hsn_sac_code": "1006", "taxable_amount": 500, "cgst": 2.5, "sgst": 2.5, "igst": 0},
        }
    )


def _seed_mandiplace_setup(stack: dict) -> None:
    stack["governance"].register_manufacturer(
        {"manufacturer_code": "MANU201", "manufacturer_id": "MANU201", "business_name": "Requester", "owner_email": "requester@example.com", "status": "ACTIVE", "city": "Pune"}
    )
    stack["governance"].register_manufacturer(
        {"manufacturer_code": "MANU202", "manufacturer_id": "MANU202", "business_name": "Supplier", "owner_email": "supplier@example.com", "status": "ACTIVE", "city": "Surat"}
    )
    stack["governance"].upsert_product(
        {
            "product_id": "PRD-MANDI-1",
            "name": "Rice Bags",
            "status": "ACTIVE",
            "visible": True,
            "available_for_mandi_network": True,
            "created_by_manufacturer_id": "MANU202",
            "created_by": "MANU202",
            "approved_mandi_price": 85,
            "mandi_price": 85,
            "unit": "bag",
        }
    )
    stack["procurement_service"].dual_inventory_service.upsert_inventory_item(
        "MANU202",
        product_id="PRD-MANDI-1",
        product_name="Rice Bags",
        unit="bag",
        self_available_qty=10,
        mandi_available_qty=50,
        visible_to_mandi=True,
    )


def test_settlement_partial_payment_and_overdue_detection(tmp_path):
    stack = _build_finance_stack(tmp_path)
    tx = stack["settlement_service"].ensure_transaction(
        transaction_type="MARKETPLACE",
        related_order_id="PUBORD-1",
        payer_role="public_buyer",
        payer_id="BUY001",
        payee_role="manufacturer",
        payee_id="MANU101",
        gross_amount=1000,
        due_date=(datetime.now(UTC).date() - timedelta(days=1)).isoformat(),
        created_by="buyer@example.com",
    )
    partial = stack["settlement_service"].record_payment(
        financial_transaction_id=tx["financial_transaction_id"],
        amount=400,
        actor_id="seller@example.com",
        payment_reference="UTR001",
    )
    overdue = stack["settlement_service"].mark_overdue_transactions()

    assert partial["status"] == "PARTIAL"
    assert partial["outstanding_balance"] == 600.0
    assert overdue[0]["status"] == "OVERDUE"


def test_invoice_generation_and_tax_fields_persist(tmp_path):
    stack = _build_finance_stack(tmp_path)
    raw = stack["governance"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Cotton",
            "available_qty": 100,
            "supply_price": 25,
            "tax_profile": {"hsn_sac_code": "5201", "cgst": 2.5, "sgst": 2.5},
            "status": "ACTIVE",
        }
    )
    invoice = stack["invoice_service"].generate_invoice(
        invoice_type="SUPPLY_INVOICE",
        related_order_id="MO-1",
        bill_from={"mahajan_id": "MAH001"},
        bill_to={"manufacturer_code": "MANU101"},
        items=[{"name": "Cotton", "qty": 10, "unit": "kg", "unit_price": 25}],
        subtotal=250,
        tax_amount=12.5,
    )

    assert raw["tax_profile"]["hsn_sac_code"] == "5201"
    assert invoice["grand_total"] == 262.5
    assert (tmp_path / "runtime" / "financial" / "invoices" / f"{invoice['invoice_id']}.json").exists()


def test_marketplace_checkout_and_payment_verification_create_finance_records(tmp_path):
    stack = _build_finance_stack(tmp_path)
    _seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD001", qty=2)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    tx = next(item for item in stack["governance"].list_financial_transactions() if item["related_order_id"] == order["public_order_id"])

    stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR999", screenshot_placeholder="https://example.com/proof.png")
    verified = stack["public_order_service"].verify_payment(order["public_order_id"], SimpleNamespace(role="manufacturer", email="seller@example.com", manufacturer_code="MANU101"), approved=True, note="ok")
    updated_tx = stack["governance"].get_financial_transaction(tx["financial_transaction_id"])

    assert verified["payment_status"] == "VERIFIED"
    assert updated_tx["status"] == "PAID"
    assert updated_tx["payment_reference"] == "UTR999"
    assert stack["invoice_service"].list_invoices()


def test_mandiplace_confirmation_creates_finance_transaction_and_invoice(tmp_path):
    stack = _build_finance_stack(tmp_path)
    _seed_mandiplace_setup(stack)
    stack["governance"].upsert_packaging_service(
        {"packaging_service_id": "PKG001", "name": "Standard Pack", "material_type": "BOX", "unit": "piece", "base_price": 10, "price_per_unit": 2, "minimum_charge": 10, "status": "ACTIVE"}
    )
    stack["governance"].upsert_courier_service(
        {"courier_service_id": "CUR001", "provider_name": "Fast Freight", "service_type": "INTERCITY", "base_price": 50, "price_per_km": 1, "price_per_kg": 1, "minimum_charge": 40, "status": "ACTIVE"}
    )
    created = stack["procurement_service"].create_mandiplace_request(
        requesting_manufacturer_id="MANU201",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 5, "unit": "bag"}],
    )
    stack["procurement_service"].assign_manufacturer_supplier(mandiplace_order_id=created["mandiplace_order_id"], supplier_manufacturer_id="MANU202", admin_email="admin@example.com")
    stack["procurement_service"].supplier_quote_mandiplace_order(mandiplace_order_id=created["mandiplace_order_id"], supplier_manufacturer_id="MANU202", supplier_unit_price=80, actor_email="supplier@example.com")
    stack["procurement_service"].set_mandiplace_manufacturer_price(mandiplace_order_id=created["mandiplace_order_id"], manufacturer_unit_price=90, admin_email="admin@example.com")
    stack["procurement_service"].apply_packaging_to_mandiplace_order(mandiplace_order_id=created["mandiplace_order_id"], packaging_service_id="PKG001", qty=5, actor_email="admin@example.com")
    stack["procurement_service"].book_courier_for_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        courier_service_id="CUR001",
        pickup_location="Surat",
        delivery_location="Pune",
        distance_km=100,
        weight_kg=50,
        actor_email="admin@example.com",
    )
    confirmed = stack["procurement_service"].confirm_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_code="MANU201",
        actor_email="requester@example.com",
    )
    finance_tx = next(item for item in stack["governance"].list_financial_transactions() if item["related_order_id"] == created["mandiplace_order_id"])

    assert confirmed["status"] == "MANUFACTURER_CONFIRMED"
    assert finance_tx["transaction_type"] == "MANDIPLACE"
    assert finance_tx["packaging_amount"] > 0
    assert finance_tx["courier_amount"] > 0
    assert stack["invoice_service"].list_invoices()


def test_dispute_creation_resolution_and_export(tmp_path):
    stack = _build_finance_stack(tmp_path)
    tx = stack["settlement_service"].ensure_transaction(
        transaction_type="SUPPLY",
        related_order_id="MO-9",
        payer_role="manufacturer",
        payer_id="MANU101",
        payee_role="mahajan",
        payee_id="MAH001",
        gross_amount=500,
        created_by="owner@example.com",
    )
    dispute = stack["dispute_service"].create_dispute(
        related_transaction_id=tx["financial_transaction_id"],
        related_order_id="MO-9",
        raised_by_role="manufacturer",
        raised_by_id="MANU101",
        reason="payment mismatch",
        evidence_refs=["proof-1"],
    )
    resolved = stack["dispute_service"].resolve_dispute(dispute_id=dispute["dispute_id"], resolution_note="Adjusted", actor_id="admin@example.com")
    export_path = stack["settlement_service"].export_rows()

    assert dispute["status"] == "OPEN"
    assert resolved["status"] == "RESOLVED"
    assert export_path.exists()
    assert stack["notifications"].rows


def test_finance_route_is_admin_only(tmp_path):
    _ = _build_finance_stack(tmp_path)
    app_context = {
        "session_user": SimpleNamespace(role="public_buyer", email="buyer@example.com"),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
    }

    assert can_access_route(SimpleNamespace(role="platform_admin", email="admin@example.com"), "Finance Operations", {"session_user": SimpleNamespace(role="platform_admin"), "security_service": SimpleNamespace(is_admin_identity=lambda _user: True)})
    assert not can_access_route(SimpleNamespace(role="public_buyer", email="buyer@example.com"), "Finance Operations", app_context)
