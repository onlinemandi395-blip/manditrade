from __future__ import annotations

from types import SimpleNamespace

from bootstrap.app_bootstrap import resolve_navigation_sections
from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime
from tests.test_public_marketplace import build_public_stack, seed_public_product


def test_public_marketplace_flow_stays_public_buyer_only(tmp_path):
    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101", mrp=500.0)
    stack["dual_inventory_service"].upsert_inventory_item(
        "MANU101",
        product_id="PRD-2026-000001",
        product_name="Rice",
        unit="bag",
        self_available_qty=10,
        mandi_available_qty=30,
    )
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    stack["public_order_service"].submit_payment_reference(order["public_order_id"], buyer["public_buyer_id"], payment_reference="UTR12345")
    verified = stack["public_order_service"].verify_payment(
        order["public_order_id"],
        SimpleNamespace(role="manufacturer", manufacturer_code="MANU101", email="seller@example.com"),
        approved=True,
    )
    sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None),
            "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )

    assert verified["status"] == "PAID"
    assert verified["payment_receiver"] == "MANU101"
    assert "Inventory" not in sections
    assert "Mandi Orders" not in sections
    assert "Raw Materials" not in sections
    assert stack["json_service"].read_json(stack["domain_paths"].ledger_path("MANU101"), {"ledgers": []}).get("ledgers", []) == []


def test_mandi_supply_flow_creates_admin_routed_dual_leg_accounting(tmp_path):
    runtime = build_runtime(tmp_path)
    runtime["governance"].register_manufacturer(
        {
            "manufacturer_code": "MANU101",
            "manufacturer_name": "Shree Agro",
            "business_name": "Shree Agro",
            "owner_email": "owner@example.com",
            "city": "Pune",
            "status": "ACTIVE",
        }
    )
    runtime["governance"].upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "name": "Supply Partner",
            "email": "mahajan@example.com",
            "mobile": "9999999999",
            "status": "ACTIVE",
        }
    )
    runtime["governance"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Cotton Suta",
            "unit": "kg",
            "category": "SUTA",
            "available_qty": 5000,
            "supply_price": 35,
            "status": "ACTIVE",
        }
    )
    procurement = build_procurement_service(runtime)
    order = procurement.create_supply_request(
        manufacturer_code="MANU101",
        raw_material_id="RM001",
        qty=1000,
        unit="kg",
        requested_by="owner@example.com",
    )
    procurement.assign_supply_to_mahajan(mandi_order_id=order["mandi_order_id"], mahajan_id="MAH001", admin_email="admin@example.com")
    procurement.quote_supply_order(
        mandi_order_id=order["mandi_order_id"],
        mahajan_id="MAH001",
        mahajan_unit_price=35,
        mahajan_email="mahajan@example.com",
    )
    priced = procurement.set_manufacturer_supply_price(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_unit_price=40,
        admin_email="admin@example.com",
    )
    procurement.confirm_supply_order(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_code="MANU101",
        actor_email="owner@example.com",
    )
    procurement.dispatch_supply_order(
        mandi_order_id=order["mandi_order_id"],
        mahajan_id="MAH001",
        actor_email="mahajan@example.com",
    )
    received = procurement.receive_supply_order(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_code="MANU101",
        actor_email="owner@example.com",
    )
    ledgers = procurement.ledger_service.list_ledgers("MANU101")

    assert priced["route_type"] == "ADMIN_ROUTED"
    assert priced["payment_receiver"] == "MAH001"
    assert priced["commission_object"]["admin_total_earning"] > 0
    assert received["status"] == "MANUFACTURER_RECEIVED"
    assert any(ledger["party_b"] == "MAH001" for ledger in ledgers)
    assert any(entry["mandi_order_id"] == order["mandi_order_id"] for entry in runtime["governance"].list_supply_ledger_entries())


def test_role_navigation_matches_final_three_network_model():
    security_service = SimpleNamespace(is_admin_identity=lambda _user: False)
    worker_service = SimpleNamespace(get_worker_by_email=lambda _email: None)

    manufacturer_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101"),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )
    mahajan_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="mahajan", email="mahajan@example.com", manufacturer_code=None),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )
    public_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )

    assert "Marketplace" in manufacturer_sections
    assert "MandiPlace" in manufacturer_sections
    assert "Supply Requests" in manufacturer_sections
    assert "Suta Mandi" in manufacturer_sections
    assert "Raw Materials" in mahajan_sections
    assert "Supply Orders" in mahajan_sections
    assert public_sections == ["Dashboard", "My Profile", "Notifications", "My Actions", "Marketplace", "Marketplace Orders", "Jobs"]
