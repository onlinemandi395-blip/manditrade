from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bootstrap.app_bootstrap import resolve_navigation_sections
from modules.marketplace.dashboard import render_marketplace_dashboard
from services.action_center_service import ActionCenterService
from services.domain_paths_service import DomainPathsService
from services.dual_inventory_service import DualInventoryService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.notification_center_service import NotificationCenterService
from services.product_catalog_service import ProductCatalogService
from services.public_buyer_service import PublicBuyerService
from services.public_cart_service import PublicCartService
from services.public_order_service import PublicOrderService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import GmailStub, LoggingStub
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.transaction_fixtures import build_order_service, current_user


class _FakeTab:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def build_public_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    governance_service = GovernanceService(tmp_path / "governance", safe_write)
    governance_service.ensure_files()
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    domain_paths = DomainPathsService(drive)
    notification_service = NotificationCenterService(
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        domain_paths_service=domain_paths,
        public_buyers_root=tmp_path / "public_buyers",
    )
    product_service = ProductCatalogService(governance_service, allocator, notification_center_service=notification_service, gmail_service=GmailStub(), admin_email="admin@example.com")
    public_buyer_service = PublicBuyerService(tmp_path / "public_buyers", safe_write, json_service, allocator)
    public_cart_service = PublicCartService(public_buyer_service, product_service, safe_write, json_service, allocator)
    dual_inventory_service = DualInventoryService(safe_write, json_service, domain_paths)
    public_order_service = PublicOrderService(
        public_orders_root=tmp_path / "public_orders",
        public_payments_root=tmp_path / "public_payments",
        public_buyer_service=public_buyer_service,
        public_cart_service=public_cart_service,
        product_catalog_service=product_service,
        dual_inventory_service=dual_inventory_service,
        notification_center_service=notification_service,
        gmail_service=GmailStub(),
        governance_service=governance_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        config={"mode": "UPI_MANUAL", "instructions": "Pay full amount upfront and enter UTR."},
    )
    return {
        "json_service": json_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "governance_service": governance_service,
        "drive": drive,
        "domain_paths": domain_paths,
        "notification_service": notification_service,
        "product_service": product_service,
        "public_buyer_service": public_buyer_service,
        "public_cart_service": public_cart_service,
        "dual_inventory_service": dual_inventory_service,
        "public_order_service": public_order_service,
    }


def seed_public_product(stack: dict, *, product_id: str, manufacturer_code: str, visibility: str = "PUBLIC", active: bool = True, public_sale: bool = True, mrp: float = 500.0):
    stack["drive"].initialize_manufacturer_workspace(manufacturer_code, f"{manufacturer_code} Traders", owner_email=f"{manufacturer_code.lower()}@example.com", city="Pune")
    stack["governance_service"].register_manufacturer(
        {
            "manufacturer_code": manufacturer_code,
            "manufacturer_name": f"{manufacturer_code} Traders",
            "business_name": f"{manufacturer_code} Traders",
            "owner_email": f"{manufacturer_code.lower()}@example.com",
            "city": "Pune",
            "status": "ACTIVE",
            "banking": {"account_holder_name": "Seller", "account_number": "", "ifsc": "", "upi_id": "seller@upi"},
        }
    )
    stack["governance_service"].upsert_product(
        {
            "product_id": product_id,
            "name": f"Product {product_id[-2:]}",
            "category": "Grain",
            "unit": "bag",
            "description": "Public marketplace product",
            "status": "ACTIVE" if active else "PROPOSED",
            "approved_visibility": visibility,
            "visibility_request": visibility,
            "approved_mrp": mrp,
            "mrp": mrp,
            "approved_mandi_price": 400.0,
            "mandi_price": 400.0,
            "suggested_mandi_price": 390.0,
            "minimum_order_qty": 1,
            "available_for_public_sale": public_sale,
            "available_for_mandi_network": True,
            "public_seller_manufacturer_id": manufacturer_code,
            "created_by": manufacturer_code,
            "created_by_manufacturer_id": manufacturer_code,
            "visible": True,
        }
    )


def test_public_marketplace_lists_only_active_public_products(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101", visibility="PUBLIC", active=True, public_sale=True)
    seed_public_product(stack, product_id="PRD-2026-000002", manufacturer_code="MANU101", visibility="PRIVATE_CLIENT", active=True, public_sale=True)
    seed_public_product(stack, product_id="PRD-2026-000003", manufacturer_code="MANU101", visibility="PUBLIC", active=False, public_sale=True)
    products = stack["product_service"].list_products(include_pending=False, viewer_role="public_buyer")
    assert [item["product_id"] for item in products] == ["PRD-2026-000001"]


def test_public_buyer_cannot_see_mandi_price(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    product = stack["product_service"].list_products(include_pending=False, viewer_role="public_buyer")[0]
    assert "mandi_price" not in product
    assert "suggested_mandi_price" not in product
    assert "approved_mandi_price" not in product


def test_public_buyer_navigation_excludes_internal_routes(tmp_path):
    public_buyer_service = SimpleNamespace(get_by_email=lambda _email: {"public_buyer_id": "PB-2026-000001"})
    app_context = {
        "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
        "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        "public_buyer_service": public_buyer_service,
    }
    sections = resolve_navigation_sections(app_context)
    assert sections == ["Dashboard", "My Profile", "Notifications", "My Actions", "Marketplace", "Marketplace Orders", "Jobs"]
    assert "Inventory" not in sections
    assert "RFQ" not in sections
    assert "Ledger" not in sections


def test_public_marketplace_uses_product_grid_markup():
    content = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")

    assert "mt-public-product-grid mt-card-grid" in content
    assert "Cart:" in content


def test_new_public_buyer_profile_starts_incomplete(tmp_path):
    stack = build_public_stack(tmp_path)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    assert buyer["profile_status"] == "INCOMPLETE"
    assert stack["public_buyer_service"].is_profile_complete(buyer) is False


def test_public_buyer_profile_save_requires_required_fields(tmp_path):
    stack = build_public_stack(tmp_path)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    with pytest.raises(ValueError, match="required"):
        stack["public_buyer_service"].validate_profile(
            {
                "full_name": "Buyer",
                "mobile": "",
                "city": "Pune",
                "state": "Maharashtra",
                "pin_code": "411001",
                "delivery_address": "Shop 1",
                "preferred_payment_mode": "UPI",
            }
        )
    updated = stack["public_buyer_service"].upsert_profile(
        buyer["public_buyer_id"],
        {
            "full_name": "Buyer",
            "mobile": "9876543210",
            "city": "Pune",
            "state": "Maharashtra",
            "pin_code": "411001",
            "delivery_address": "Shop 1",
            "landmark": "Near gate",
            "preferred_payment_mode": "UPI",
        },
    )
    assert updated["profile_status"] == "COMPLETE"
    assert updated["delivery_address"] == "Shop 1"


def test_invalid_public_buyer_mobile_and_pin_are_rejected(tmp_path):
    stack = build_public_stack(tmp_path)
    with pytest.raises(ValueError, match="10 digits"):
        stack["public_buyer_service"].validate_profile(
            {
                "full_name": "Buyer",
                "mobile": "12345",
                "city": "Pune",
                "state": "Maharashtra",
                "pin_code": "411001",
                "delivery_address": "Shop 1",
                "preferred_payment_mode": "UPI",
            }
        )


def test_incomplete_public_buyer_marketplace_shows_onboarding(monkeypatch, tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    hits: list[str] = []
    monkeypatch.setattr("modules.marketplace.dashboard.render_public_buyer_profile_setup", lambda _ctx, welcome_mode=False: hits.append(f"welcome:{welcome_mode}"))
    monkeypatch.setattr("modules.marketplace.dashboard.render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_metric_grid", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_showcase_strip", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_section_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_html", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.columns", lambda *_args, **_kwargs: (SimpleNamespace(text_input=lambda *a, **k: "", selectbox=lambda *a, **k: "All"), SimpleNamespace(selectbox=lambda *a, **k: "All")))
    monkeypatch.setattr("modules.marketplace.dashboard.st.selectbox", lambda _label, options, **_kwargs: options[0])
    monkeypatch.setattr("modules.marketplace.dashboard.st.number_input", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("modules.marketplace.dashboard.st.button", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("modules.marketplace.dashboard.st.json", lambda *_args, **_kwargs: None)
    app_context = {
        "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com"),
        "product_catalog_service": stack["product_service"],
        "public_buyer_service": stack["public_buyer_service"],
        "public_cart_service": stack["public_cart_service"],
        "public_order_service": stack["public_order_service"],
    }
    render_marketplace_dashboard(app_context)
    assert hits == ["welcome:True"]


def test_complete_public_buyer_marketplace_skips_onboarding(monkeypatch, tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_buyer_service"].upsert_profile(
        buyer["public_buyer_id"],
        {
            "full_name": "Buyer",
            "mobile": "9876543210",
            "city": "Pune",
            "state": "Maharashtra",
            "pin_code": "411001",
            "delivery_address": "Flat 101",
            "preferred_payment_mode": "UPI",
        },
    )
    hits: list[str] = []
    monkeypatch.setattr("modules.marketplace.dashboard.render_public_buyer_profile_setup", lambda _ctx, welcome_mode=False: hits.append(f"welcome:{welcome_mode}"))
    monkeypatch.setattr("modules.marketplace.dashboard.render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_metric_grid", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_showcase_strip", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_section_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_html", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.columns", lambda *_args, **_kwargs: (SimpleNamespace(text_input=lambda *a, **k: "", selectbox=lambda *a, **k: "All"), SimpleNamespace(selectbox=lambda *a, **k: "All")))
    monkeypatch.setattr("modules.marketplace.dashboard.st.selectbox", lambda _label, options, **_kwargs: options[0])
    monkeypatch.setattr("modules.marketplace.dashboard.st.number_input", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("modules.marketplace.dashboard.st.button", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("modules.marketplace.dashboard.st.json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.tabs", lambda *_args, **_kwargs: (_FakeTab(), _FakeTab()))
    monkeypatch.setattr("modules.marketplace.dashboard.st.info", lambda *args, **kwargs: None)
    app_context = {
        "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com"),
        "product_catalog_service": stack["product_service"],
        "public_buyer_service": stack["public_buyer_service"],
        "public_cart_service": stack["public_cart_service"],
        "public_order_service": stack["public_order_service"],
    }
    render_marketplace_dashboard(app_context)
    assert hits == []
    with pytest.raises(ValueError, match="6 digits"):
        stack["public_buyer_service"].validate_profile(
            {
                "full_name": "Buyer",
                "mobile": "9876543210",
                "city": "Pune",
                "state": "Maharashtra",
                "pin_code": "4110",
                "delivery_address": "Shop 1",
                "preferred_payment_mode": "UPI",
            }
        )


def test_public_cart_calculates_total_from_mrp_only(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101", mrp=500.0)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    cart = stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=2)
    assert cart["subtotal"] == 1000.0
    assert cart["items"][0]["mrp"] == 500.0


def test_public_order_requires_upfront_payment(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101", mrp=500.0)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=2)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    assert order["status"] == "PAYMENT_PENDING"
    assert order["total_amount"] == 1000.0
    assert order["payment_mode"] == "UPI_MANUAL"


def test_payment_reference_submission_changes_status_correctly(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    updated = stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR12345")
    assert updated["payment_status"] == "SUBMITTED"
    assert updated["status"] == "PAYMENT_PENDING"


def test_seller_verification_reserves_self_inventory_only(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    stack["dual_inventory_service"].upsert_inventory_item("MANU101", product_id="PRD-2026-000001", product_name="Rice", unit="bag", self_available_qty=10, mandi_available_qty=30)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=2)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR12345")
    verified = stack["public_order_service"].verify_payment(order["public_order_id"], current_user("MANU101"), approved=True)
    inventory = stack["json_service"].read_json(stack["domain_paths"].inventory_path("MANU101"), {})
    assert verified["status"] == "PAID"
    assert inventory["items"][0]["self_inventory"]["reserved_qty"] == 2
    assert inventory["items"][0]["mandi_inventory"]["reserved_qty"] == 0
    assert inventory["items"][0]["mandi_inventory"]["available_qty"] == 30


def test_public_order_does_not_create_ledger_by_default(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    stack["dual_inventory_service"].upsert_inventory_item("MANU101", product_id="PRD-2026-000001", product_name="Rice", unit="bag", self_available_qty=10, mandi_available_qty=30)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR12345")
    stack["public_order_service"].verify_payment(order["public_order_id"], current_user("MANU101"), approved=True)
    assert stack["json_service"].read_json(stack["domain_paths"].ledger_path("MANU101"), {"ledgers": []}).get("ledgers", []) == []


def test_multi_seller_cart_is_blocked(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    seed_public_product(stack, product_id="PRD-2026-000002", manufacturer_code="MANU202")
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    try:
        stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000002", qty=1)
    except ValueError as exc:
        assert "Multi-seller" in str(exc)
    else:
        raise AssertionError("Expected multi-seller cart to be blocked.")


def test_private_client_flow_remains_proposal_based(tmp_path):
    runtime = {
        "json_service": JsonServiceStub(),
        "logging_service": LoggingStub(),
        "file_lock_service": FileLockService(),
        "safe_write": SafeDriveWriteService(
            json_service=JsonServiceStub(),
            file_lock_service=FileLockService(),
            schema_validation_service=SchemaValidationService(),
            backups_root=tmp_path / "backups_private",
            logging_service=LoggingStub(),
            version_history_root=tmp_path / "history_private",
        ),
    }
    from tests.helpers.transaction_fixtures import build_runtime, seed_inventory

    tx_runtime = build_runtime(tmp_path / "private")
    seed_inventory(tx_runtime, "MANU101", self_qty=100, mandi_qty=10)
    service = build_order_service(tx_runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 5, "unit": "kg", "mrp": 50, "mandi_price": 40}],
        {"payment_modes": ["cash", "upi"], "upfront_percentage": 30, "ledger_days": 10, "freestyle_note": "proposal"},
    )
    assert order["status"] == "READY_TO_CONFIRM"
    assert "payment_proposal" in order


def test_public_order_actions_are_exposed_for_buyer_and_seller(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    stack["dual_inventory_service"].upsert_inventory_item("MANU101", product_id="PRD-2026-000001", product_name="Rice", unit="bag", self_available_qty=10, mandi_available_qty=30)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    buyer_actions = ActionCenterService(
        governance_service=SimpleNamespace(list_products=lambda: [], list_manufacturers=lambda: []),
        gmail_service=GmailStub(),
        notification_center_service=stack["notification_service"],
        ledger_service=SimpleNamespace(list_ledgers=lambda _manufacturer: []),
        order_query_service=SimpleNamespace(list_orders=lambda _manufacturer: [], list_orders_for_client=lambda _manufacturer, _email: []),
        procurement_query_service=SimpleNamespace(list_procurement_requests=lambda _manufacturer: []),
        dual_inventory_service=SimpleNamespace(list_inventory=lambda _manufacturer: {"items": []}),
        public_order_service=stack["public_order_service"],
    ).get_actions(SimpleNamespace(role="public_buyer", email="buyer@example.com"))
    stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR12345")
    seller_actions = ActionCenterService(
        governance_service=SimpleNamespace(list_products=lambda: [], list_manufacturers=lambda: []),
        gmail_service=GmailStub(),
        notification_center_service=stack["notification_service"],
        ledger_service=SimpleNamespace(list_ledgers=lambda _manufacturer: []),
        order_query_service=SimpleNamespace(list_orders=lambda _manufacturer: [], list_orders_for_client=lambda _manufacturer, _email: []),
        procurement_query_service=SimpleNamespace(list_procurement_requests=lambda _manufacturer: []),
        dual_inventory_service=SimpleNamespace(list_inventory=lambda _manufacturer: {"items": []}),
        public_order_service=stack["public_order_service"],
    ).get_actions(SimpleNamespace(role="manufacturer", manufacturer_code="MANU101", email="seller@example.com"))
    assert any(item["type"] == "COMPLETE_PUBLIC_PAYMENT" for item in buyer_actions)
    assert any(item["type"] == "VERIFY_PUBLIC_PAYMENT" for item in seller_actions)
