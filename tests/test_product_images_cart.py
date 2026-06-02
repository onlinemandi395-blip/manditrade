from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.marketplace.dashboard import render_marketplace_dashboard
from services.cart_service import CartService
from services.domain_paths_service import DomainPathsService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.image_service import ImageService
from services.notification_center_service import NotificationCenterService
from services.product_catalog_service import ProductCatalogService
from services.public_buyer_service import PublicBuyerService
from services.public_cart_service import PublicCartService
from services.public_order_service import PublicOrderService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import GmailStub, LoggingStub
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.transaction_fixtures import build_runtime, build_procurement_service


class _FakeTab:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def build_stack(tmp_path: Path):
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
    image_service = ImageService(uploads_root=tmp_path / "uploads")
    product_service = ProductCatalogService(
        governance_service,
        allocator,
        notification_center_service=notification_service,
        gmail_service=GmailStub(),
        admin_email="admin@example.com",
        image_service=image_service,
    )
    public_buyer_service = PublicBuyerService(tmp_path / "public_buyers", safe_write, json_service, allocator)
    runtime = build_runtime(tmp_path / "tx")
    procurement_service = build_procurement_service(runtime)
    cart_service = CartService(
        carts_root=tmp_path / "carts",
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        product_catalog_service=product_service,
        governance_service=governance_service,
        procurement_transaction_service=procurement_service,
    )
    public_cart_service = PublicCartService(public_buyer_service, product_service, safe_write, json_service, allocator, cart_service=cart_service)
    public_order_service = PublicOrderService(
        public_orders_root=tmp_path / "public_orders",
        public_payments_root=tmp_path / "public_payments",
        public_buyer_service=public_buyer_service,
        public_cart_service=public_cart_service,
        product_catalog_service=product_service,
        dual_inventory_service=runtime["drive"],
        notification_center_service=notification_service,
        gmail_service=GmailStub(),
        governance_service=governance_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        config={"mode": "UPI_MANUAL"},
    )
    cart_service.public_order_service = public_order_service
    return {
        "json_service": json_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "governance_service": governance_service,
        "drive": drive,
        "domain_paths": domain_paths,
        "notification_service": notification_service,
        "image_service": image_service,
        "product_service": product_service,
        "public_buyer_service": public_buyer_service,
        "public_cart_service": public_cart_service,
        "public_order_service": public_order_service,
        "cart_service": cart_service,
        "procurement_service": procurement_service,
    }


def seed_public_product(stack: dict, *, product_id: str = "PRD-2026-000001", manufacturer_code: str = "MANU101", image_url: str = ""):
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
            "name": "Catalog Rice",
            "category": "Grain",
            "unit": "bag",
            "description": "Public marketplace product",
            "status": "ACTIVE",
            "approved_visibility": "PUBLIC",
            "visibility_request": "PUBLIC",
            "approved_marketplace_price": 500.0,
            "marketplace_price": 500.0,
            "approved_mandi_price": 400.0,
            "mandi_price": 400.0,
            "minimum_order_qty": 1,
            "available_for_public_sale": True,
            "available_for_mandi_network": True,
            "public_seller_manufacturer_id": manufacturer_code,
            "created_by": manufacturer_code,
            "created_by_manufacturer_id": manufacturer_code,
            "visible": True,
            "image_url": image_url,
        }
    )


def test_product_proposal_accepts_image_url(tmp_path):
    stack = build_stack(tmp_path)
    product = stack["product_service"].propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="bag",
        image_url="https://example.com/rice.jpg",
        image_alt_text="Rice bag",
    )
    assert product["image_url"] == "https://example.com/rice.jpg"
    assert product["image_status"] == "URL"


def test_raw_material_accepts_image_url(tmp_path):
    stack = build_stack(tmp_path)
    metadata = stack["image_service"].normalize_image_metadata(image_url="https://example.com/cotton.jpg", image_alt_text="Cotton bale")
    raw = stack["governance_service"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Cotton",
            "supply_price": 10,
            "available_qty": 50,
            **metadata,
        }
    )
    assert raw["image_url"] == "https://example.com/cotton.jpg"
    assert raw["image_status"] == "URL"


def test_missing_image_uses_placeholder(tmp_path):
    image = ImageService(uploads_root=tmp_path / "uploads").get_display_image({"name": "Fallback Product"})
    assert image["src"].startswith("data:image/svg+xml")


def test_public_buyer_sees_marketplace_price_only(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    product = stack["product_service"].list_products(include_pending=False, viewer_role="public_buyer")[0]
    assert "marketplace_price" in product
    assert "mandi_price" not in product
    assert "supply_price" not in product


def test_public_buyer_can_add_to_cart_and_cart_subtotal_works(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    cart = stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=2)
    assert cart["subtotal"] == 1000.0
    assert cart["owner_role"] == "public_buyer"


def test_checkout_creates_marketplace_order(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["cart_service"].checkout("public_buyer", buyer["public_buyer_id"], cart_type="MARKETPLACE", checkout_context={})
    assert order["status"] == "PAYMENT_PENDING"
    assert order["public_order_id"]


def test_manufacturer_mandiplace_request_creates_admin_routed_order(tmp_path):
    stack = build_stack(tmp_path)
    stack["governance_service"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Cotton",
            "category": "RAW_MATERIAL",
            "unit": "kg",
            "available_qty": 100,
            "supply_price": 25,
            "status": "ACTIVE",
        }
    )
    created = stack["cart_service"].add_item("manufacturer", "MANU101", cart_type="MANDIPLACE", item_id="RM001", qty=3)
    assert created["subtotal"] == 75.0
    orders = stack["cart_service"].checkout(
        "manufacturer",
        "MANU101",
        cart_type="MANDIPLACE",
        checkout_context={"manufacturer_code": "MANU101", "requester_email": "owner@example.com"},
    )
    assert orders[0]["route_type"] == "ADMIN_ROUTED"
    assert orders[0]["status"] == "REQUESTED_BY_MANUFACTURER"


def test_worker_cannot_add_to_cart(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    try:
        stack["cart_service"].add_item("worker", "WORK001", cart_type="MARKETPLACE", item_id="PRD-2026-000001", qty=1)
    except PermissionError:
        pass
    else:
        raise AssertionError("Worker should not be allowed to add marketplace items to cart.")


def test_marketplace_cards_render(monkeypatch, tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
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
    monkeypatch.setattr("modules.marketplace.dashboard.render_product_card", lambda **kwargs: hits.append(kwargs["title"]) or False)
    monkeypatch.setattr("modules.marketplace.dashboard.render_page_header", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_metric_grid", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_showcase_strip", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_section_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.render_html", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.columns", lambda *_args, **_kwargs: (SimpleNamespace(text_input=lambda *a, **k: "", selectbox=lambda *a, **k: "All"), SimpleNamespace(selectbox=lambda *a, **k: "All")))
    monkeypatch.setattr("modules.marketplace.dashboard.st.selectbox", lambda _label, options, **_kwargs: options[0])
    monkeypatch.setattr("modules.marketplace.dashboard.st.number_input", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr("modules.marketplace.dashboard.st.button", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("modules.marketplace.dashboard.st.tabs", lambda *_args, **_kwargs: (_FakeTab(), _FakeTab()))
    monkeypatch.setattr("modules.marketplace.dashboard.st.info", lambda *args, **kwargs: None)
    monkeypatch.setattr("modules.marketplace.dashboard.st.success", lambda *args, **kwargs: None)
    app_context = {
        "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com"),
        "product_catalog_service": stack["product_service"],
        "public_buyer_service": stack["public_buyer_service"],
        "public_cart_service": stack["public_cart_service"],
        "public_order_service": stack["public_order_service"],
        "image_service": stack["image_service"],
    }
    render_marketplace_dashboard(app_context)
    assert hits == ["Catalog Rice"]
