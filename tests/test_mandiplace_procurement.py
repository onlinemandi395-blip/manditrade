from __future__ import annotations

from types import SimpleNamespace

from bootstrap.route_registry import can_access_route
from services.event_notification_service import EventNotificationService
from services.gmail_service import GmailService
from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime


class _FakeGmail:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def enqueue_message(self, recipient_email, subject, body, event_type, deep_link="", metadata=None):
        self.messages.append({"email": recipient_email, "subject": subject, "event_type": event_type, "deep_link": deep_link})


class _FakeNotifications:
    def __init__(self) -> None:
        self.in_app: list[dict[str, str]] = []

    def create_notification(self, owner_id, **kwargs):
        self.in_app.append({"owner_id": owner_id, **kwargs})
        return self.in_app[-1]

    def create_public_notification(self, owner_id, **kwargs):
        self.in_app.append({"owner_id": owner_id, **kwargs})
        return self.in_app[-1]


def _seed_manufacturers_and_product(runtime: dict) -> None:
    runtime["governance"].register_manufacturer(
        {
            "manufacturer_code": "MANU101",
            "manufacturer_id": "MANU101",
            "business_name": "Requester Mills",
            "owner_email": "requester@example.com",
            "status": "ACTIVE",
            "city": "Pune",
        }
    )
    runtime["governance"].register_manufacturer(
        {
            "manufacturer_code": "MANU202",
            "manufacturer_id": "MANU202",
            "business_name": "Supplier Mills",
            "owner_email": "supplier@example.com",
            "status": "ACTIVE",
            "city": "Surat",
        }
    )
    runtime["governance"].upsert_product(
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
    inventory_service = build_procurement_service(runtime).dual_inventory_service
    inventory_service.upsert_inventory_item(
        "MANU202",
        product_id="PRD-MANDI-1",
        product_name="Rice Bags",
        unit="bag",
        self_available_qty=20,
        mandi_available_qty=40,
        visible_to_mandi=True,
    )


def test_manufacturer_creates_admin_routed_mandiplace_order(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    procurement = build_procurement_service(runtime)

    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 10, "unit": "bag"}],
    )

    assert created["status"] == "REQUESTED_BY_MANUFACTURER"
    assert created["supplier_manufacturer_id"] == ""


def test_admin_can_assign_only_eligible_supplier_and_not_requester(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    procurement = build_procurement_service(runtime)
    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 10, "unit": "bag"}],
    )

    eligible = procurement.list_eligible_manufacturer_suppliers(mandiplace_order_id=created["mandiplace_order_id"])
    assert [item["manufacturer_code"] for item in eligible] == ["MANU202"]

    try:
        procurement.assign_manufacturer_supplier(
            mandiplace_order_id=created["mandiplace_order_id"],
            supplier_manufacturer_id="MANU101",
            admin_email="admin@example.com",
        )
    except ValueError as exc:
        assert "cannot be the same" in str(exc)
    else:
        raise AssertionError("Requester should not be assignable as supplier.")

    assigned = procurement.assign_manufacturer_supplier(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        admin_email="admin@example.com",
    )
    assert assigned["status"] == "SUPPLIER_ASSIGNED"


def test_supplier_can_quote_and_admin_can_set_price(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    procurement = build_procurement_service(runtime)
    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 10, "unit": "bag"}],
    )
    procurement.assign_manufacturer_supplier(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        admin_email="admin@example.com",
    )

    quoted = procurement.supplier_quote_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        supplier_unit_price=75,
        actor_email="supplier@example.com",
    )
    priced = procurement.set_mandiplace_manufacturer_price(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_unit_price=90,
        admin_email="admin@example.com",
    )

    assert quoted["status"] == "SUPPLIER_QUOTED"
    assert priced["status"] == "ADMIN_PRICE_SET"
    assert priced["cost_breakdown"]["goods_amount"] == 900.0
    assert priced["cost_breakdown"]["spread"] == 150.0


def test_packaging_and_courier_service_crud_and_final_payable(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    governance = runtime["governance"]
    packaging = governance.upsert_packaging_service(
        {
            "packaging_service_id": "PKG-0001",
            "name": "Standard Box Packing",
            "material_type": "BOX",
            "unit": "piece",
            "base_price": 20,
            "price_per_unit": 2,
            "minimum_charge": 10,
            "status": "ACTIVE",
        }
    )
    courier = governance.upsert_courier_service(
        {
            "courier_service_id": "COURIER-0001",
            "provider_name": "Fast Freight",
            "service_type": "INTERCITY",
            "base_price": 50,
            "price_per_km": 3,
            "price_per_kg": 1,
            "minimum_charge": 40,
            "status": "ACTIVE",
        }
    )
    procurement = build_procurement_service(runtime)
    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 10, "unit": "bag"}],
    )
    procurement.assign_manufacturer_supplier(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        admin_email="admin@example.com",
    )
    procurement.supplier_quote_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        supplier_unit_price=75,
        actor_email="supplier@example.com",
    )
    procurement.set_mandiplace_manufacturer_price(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_unit_price=90,
        admin_email="admin@example.com",
    )
    packaged = procurement.apply_packaging_to_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        packaging_service_id=packaging["packaging_service_id"],
        qty=10,
        actor_email="admin@example.com",
    )
    couriered = procurement.book_courier_for_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        courier_service_id=courier["courier_service_id"],
        pickup_location="Surat",
        delivery_location="Pune",
        distance_km=100,
        weight_kg=200,
        actor_email="admin@example.com",
    )

    assert packaged["packaging"]["total_packaging_cost"] == 40.0
    assert couriered["courier"]["courier_cost"] == 550.0
    assert couriered["cost_breakdown"]["final_payable"] == 1490.0


def test_confirm_dispatch_receive_creates_ledgers_and_commission(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    governance = runtime["governance"]
    governance.upsert_packaging_service(
        {
            "packaging_service_id": "PKG-0001",
            "name": "Standard Box Packing",
            "material_type": "BOX",
            "unit": "piece",
            "base_price": 20,
            "price_per_unit": 2,
            "minimum_charge": 10,
            "status": "ACTIVE",
        }
    )
    governance.upsert_courier_service(
        {
            "courier_service_id": "COURIER-0001",
            "provider_name": "Fast Freight",
            "service_type": "INTERCITY",
            "base_price": 50,
            "price_per_km": 3,
            "price_per_kg": 1,
            "minimum_charge": 40,
            "status": "ACTIVE",
        }
    )
    procurement = build_procurement_service(runtime)
    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 10, "unit": "bag"}],
    )
    procurement.assign_manufacturer_supplier(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        admin_email="admin@example.com",
    )
    procurement.supplier_quote_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        supplier_unit_price=75,
        actor_email="supplier@example.com",
    )
    procurement.set_mandiplace_manufacturer_price(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_unit_price=90,
        admin_email="admin@example.com",
    )
    procurement.apply_packaging_to_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        packaging_service_id="PKG-0001",
        qty=10,
        actor_email="admin@example.com",
    )
    procurement.book_courier_for_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        courier_service_id="COURIER-0001",
        pickup_location="Surat",
        delivery_location="Pune",
        distance_km=100,
        weight_kg=200,
        actor_email="admin@example.com",
    )
    confirmed = procurement.confirm_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_code="MANU101",
        actor_email="requester@example.com",
    )
    dispatched = procurement.dispatch_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        actor_email="supplier@example.com",
    )
    procurement.update_mandiplace_courier_status(
        mandiplace_order_id=created["mandiplace_order_id"],
        actor_email="admin@example.com",
        status="DELIVERED",
    )
    received = procurement.receive_mandiplace_order(
        mandiplace_order_id=created["mandiplace_order_id"],
        manufacturer_code="MANU101",
        actor_email="requester@example.com",
    )

    entries = procurement.ledger_service.list_ledger_entries("MANU101")
    scopes = {entry["metadata"].get("ledger_scope") for entry in entries}
    assert confirmed["commission"]["admin_commission"] == 75.0
    assert dispatched["status"] == "SUPPLIER_DISPATCHED"
    assert received["status"] == "RECEIVED"
    assert {"mandiplace_ledger", "mandiplace_commission", "mandiplace_service"} <= scopes


def test_notifications_emitted_for_mandiplace_flow_and_rbac_stays_scoped(tmp_path):
    runtime = build_runtime(tmp_path)
    _seed_manufacturers_and_product(runtime)
    notification_sink = _FakeNotifications()
    gmail_sink = _FakeGmail()
    event_service = EventNotificationService(
        notification_center_service=notification_sink,
        gmail_service=gmail_sink,
        governance_service=runtime["governance"],
        public_buyer_service=SimpleNamespace(),
        notification_rules={"events": {}},
    )
    procurement = build_procurement_service(runtime)
    procurement.event_notification_service = event_service
    created = procurement.create_mandiplace_request(
        requesting_manufacturer_id="MANU101",
        requested_by="requester@example.com",
        items=[{"product_id": "PRD-MANDI-1", "name": "Rice Bags", "qty": 5, "unit": "bag"}],
    )
    procurement.assign_manufacturer_supplier(
        mandiplace_order_id=created["mandiplace_order_id"],
        supplier_manufacturer_id="MANU202",
        admin_email="admin@example.com",
    )

    event_types = {item["notification_type"] for item in notification_sink.in_app}
    app_context = {"security_service": SimpleNamespace(is_admin_identity=lambda _user: False), "session_user": None}
    assert "MANDIPLACE_ORDER_CREATED" in event_types
    assert "SUPPLIER_ASSIGNED" in event_types
    assert can_access_route(SimpleNamespace(role="public_buyer"), "MandiPlace", app_context) is False
    assert can_access_route(SimpleNamespace(role="worker"), "MandiPlace", app_context) is False
    assert can_access_route(SimpleNamespace(role="mahajan"), "MandiPlace", app_context) is False
