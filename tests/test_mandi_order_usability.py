from __future__ import annotations

from types import SimpleNamespace

from bootstrap.route_registry import can_access_route
from modules.procurement.dashboard import (
    build_supply_order_detail,
    filter_supply_orders,
    get_mandi_timeline_labels,
    get_mandi_timeline_steps,
    get_supply_order_role_actions,
)
from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime


def test_mandi_timeline_lists_full_status_flow():
    assert get_mandi_timeline_steps() == [
        "REQUESTED_BY_MANUFACTURER",
        "ADMIN_REVIEWING",
        "SENT_TO_MAHAJAN",
        "MAHAJAN_QUOTED",
        "ADMIN_PRICE_SET",
        "MANUFACTURER_CONFIRMED",
        "MAHAJAN_DISPATCHED",
        "MANUFACTURER_RECEIVED",
        "CLOSED",
    ]
    labels = get_mandi_timeline_labels()
    assert labels["REQUESTED_BY_MANUFACTURER"] == "Manufacturer Requested"
    assert labels["MAHAJAN_DISPATCHED"] == "Mahajan Dispatched"
    assert labels["CLOSED"] == "Closed"


def test_role_specific_mandi_actions_are_scoped():
    admin_request = {"status": "REQUESTED_BY_MANUFACTURER"}
    admin_close = {"status": "MANUFACTURER_RECEIVED"}
    mahajan_quote = {"status": "SENT_TO_MAHAJAN"}
    mahajan_dispatch = {"status": "MANUFACTURER_CONFIRMED"}
    manufacturer_confirm = {"status": "ADMIN_PRICE_SET"}
    manufacturer_receive = {"status": "MAHAJAN_DISPATCHED"}

    assert get_supply_order_role_actions("platform_admin", admin_request) == ["Assign Mahajan"]
    assert get_supply_order_role_actions("platform_admin", admin_close) == ["Close Order"]
    assert get_supply_order_role_actions("mahajan", mahajan_quote) == ["Submit Quote"]
    assert get_supply_order_role_actions("mahajan", mahajan_dispatch) == ["Dispatch Order"]
    assert get_supply_order_role_actions("manufacturer", manufacturer_confirm) == ["Confirm Admin Price"]
    assert get_supply_order_role_actions("manufacturer", manufacturer_receive) == ["Mark Received"]
    assert get_supply_order_role_actions("public_buyer", manufacturer_receive) == []


def test_dashboard_cards_filter_supply_orders_by_status():
    orders = [
        {"mandi_order_id": "MO-1", "status": "REQUESTED_BY_MANUFACTURER"},
        {"mandi_order_id": "MO-2", "status": "SENT_TO_MAHAJAN"},
        {"mandi_order_id": "MO-3", "status": "ADMIN_PRICE_SET"},
        {"mandi_order_id": "MO-4", "status": "MAHAJAN_DISPATCHED"},
        {"mandi_order_id": "MO-5", "status": "MANUFACTURER_RECEIVED"},
        {"mandi_order_id": "MO-6", "status": "CLOSED"},
    ]

    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "OPEN_REQUESTS")] == ["MO-1", "MO-2"]
    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "AWAITING_MAHAJAN_QUOTE")] == ["MO-2"]
    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "AWAITING_MANUFACTURER_CONFIRMATION")] == ["MO-3"]
    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "DISPATCHED")] == ["MO-4"]
    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "RECEIVED")] == ["MO-5"]
    assert [item["mandi_order_id"] for item in filter_supply_orders(orders, "CLOSED")] == ["MO-6"]


def test_supply_order_detail_contains_required_fields():
    detail = build_supply_order_detail(
        {
            "mandi_order_id": "MO-1",
            "manufacturer_id": "MANU101",
            "mahajan_id": "MAH001",
            "raw_material_id": "RM001",
            "qty": 1000,
            "unit": "kg",
            "status": "ADMIN_PRICE_SET",
            "mahajan_unit_price": 35,
            "manufacturer_unit_price": 40,
            "commission_object": {"admin_total_earning": 2850},
        },
        role="manufacturer",
        raw_materials={"RM001": {"raw_material_id": "RM001", "name": "Raw Rice"}},
        mahajans={"MAH001": {"mahajan_id": "MAH001", "business_name": "Rice Supply Co"}},
        supply_ledger_entries=[{"mandi_order_id": "MO-1", "status": "PENDING"}],
        mandi_ledger_entries=[{"status": "PENDING", "metadata": {"supply_order": "MO-1"}}],
    )

    assert detail["order_id"] == "MO-1"
    assert detail["manufacturer"] == "MANU101"
    assert detail["mahajan"] == "Rice Supply Co"
    assert "Raw Rice" in detail["raw_material_items"]
    assert detail["mahajan_price"] == 35
    assert detail["manufacturer_price"] == 40
    assert detail["admin_earning"] == 2850
    assert detail["ledger_status"]["supply_ledger"] == "PENDING"
    assert detail["ledger_status"]["mandi_ledger"] == "PENDING"
    assert detail["next_action"] == "Confirm Admin Price"


def test_raw_material_and_product_pages_keep_labels_separate():
    raw_material_content = open("modules/raw_materials/dashboard.py", encoding="utf-8").read()
    product_content = open("modules/products/dashboard.py", encoding="utf-8").read()

    assert "Raw Materials belong to the mahajan/admin supply layer" in raw_material_content
    assert "This page is for supply inputs, not finished products." in raw_material_content
    assert "Govern finished products for catalog selling" in product_content
    assert "Raw-material supply belongs on the Raw Materials and Mandi Orders pages." in product_content


def test_mandi_order_rbac_still_blocks_wrong_roles():
    app_context = {"security_service": SimpleNamespace(is_admin_identity=lambda _user: False)}
    manufacturer = SimpleNamespace(role="manufacturer")
    mahajan = SimpleNamespace(role="mahajan")
    public_buyer = SimpleNamespace(role="public_buyer")
    public_buyer = SimpleNamespace(role="public_buyer")

    assert can_access_route(manufacturer, "Mandi Orders", app_context) is True
    assert can_access_route(mahajan, "Mandi Orders", app_context) is True
    assert can_access_route(public_buyer, "Mandi Orders", app_context) is False


def test_admin_can_cancel_and_close_supply_orders(tmp_path):
    runtime = build_runtime(tmp_path)
    runtime["governance"].upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Rice Supply Co",
            "owner_name": "Supplier",
            "email": "mahajan@example.com",
            "status": "ACTIVE",
        }
    )
    runtime["governance"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Raw Rice",
            "unit": "kg",
            "available_qty": 5000,
            "supply_price": 35,
            "status": "ACTIVE",
        }
    )
    procurement = build_procurement_service(runtime)

    cancellable = procurement.create_supply_request(
        manufacturer_code="MANU101",
        raw_material_id="RM001",
        qty=100,
        unit="kg",
        requested_by="buyer@example.com",
    )
    cancelled = procurement.cancel_supply_order(
        mandi_order_id=cancellable["mandi_order_id"],
        admin_email="admin@example.com",
        reason="Manufacturer changed plan",
    )
    assert cancelled["status"] == "CANCELLED"

    order = procurement.create_supply_request(
        manufacturer_code="MANU101",
        raw_material_id="RM001",
        qty=1000,
        unit="kg",
        requested_by="buyer@example.com",
    )
    procurement.assign_supply_to_mahajan(mandi_order_id=order["mandi_order_id"], mahajan_id="MAH001", admin_email="admin@example.com")
    procurement.quote_supply_order(
        mandi_order_id=order["mandi_order_id"],
        mahajan_id="MAH001",
        mahajan_unit_price=35,
        mahajan_email="mahajan@example.com",
    )
    procurement.set_manufacturer_supply_price(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_unit_price=40,
        admin_email="admin@example.com",
        mahajan_fee_percent=1,
    )
    procurement.confirm_supply_order(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_code="MANU101",
        actor_email="buyer@example.com",
    )
    procurement.dispatch_supply_order(
        mandi_order_id=order["mandi_order_id"],
        mahajan_id="MAH001",
        actor_email="mahajan@example.com",
    )
    received = procurement.receive_supply_order(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_code="MANU101",
        actor_email="buyer@example.com",
    )
    closed = procurement.close_supply_order(
        mandi_order_id=order["mandi_order_id"],
        admin_email="admin@example.com",
    )

    assert received["status"] == "MANUFACTURER_RECEIVED"
    assert closed["status"] == "CLOSED"
    assert [item["status"] for item in closed["internal_status_history"]][-2:] == ["MANUFACTURER_RECEIVED", "CLOSED"]
