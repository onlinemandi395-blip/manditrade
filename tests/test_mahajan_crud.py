from __future__ import annotations

from tests.helpers.transaction_fixtures import build_runtime


def test_mahajan_crud_create_update_delete_without_dependencies(tmp_path):
    runtime = build_runtime(tmp_path)
    governance = runtime["governance"]

    created = governance.upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Supply House",
            "owner_name": "Aakash",
            "email": "mahajan@example.com",
            "mobile": "9999999999",
            "city": "Pune",
            "status": "INVITED",
            "notes": "new supplier",
        }
    )
    updated = governance.upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Supply House Updated",
            "owner_name": "Aakash Kumar",
            "email": "mahajan@example.com",
            "mobile": "8888888888",
            "city": "Mumbai",
            "status": "ACTIVE",
            "notes": "approved",
        }
    )

    assert created["mahajan_id"] == "MAH001"
    assert updated["business_name"] == "Supply House Updated"
    assert governance.get_mahajan("MAH001")["status"] == "ACTIVE"

    deleted = governance.delete_mahajan("MAH001")
    assert deleted is True
    assert governance.get_mahajan("MAH001") is None


def test_mahajan_delete_blocked_when_raw_materials_exist(tmp_path):
    runtime = build_runtime(tmp_path)
    governance = runtime["governance"]
    governance.upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Supply House",
            "owner_name": "Aakash",
            "email": "mahajan@example.com",
            "status": "ACTIVE",
        }
    )
    governance.upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Raw Rice",
            "unit": "kg",
            "available_qty": 500,
            "supply_price": 35,
            "status": "ACTIVE",
        }
    )

    try:
        governance.delete_mahajan("MAH001")
    except ValueError as exc:
        assert "raw materials" in str(exc).lower()
    else:
        raise AssertionError("Expected raw-material dependency to block delete.")


def test_mahajan_delete_blocked_when_open_supply_orders_exist(tmp_path):
    runtime = build_runtime(tmp_path)
    governance = runtime["governance"]
    governance.upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Supply House",
            "owner_name": "Aakash",
            "email": "mahajan@example.com",
            "status": "ACTIVE",
        }
    )
    governance.upsert_supply_order(
        {
            "mandi_order_id": "MO-001",
            "mahajan_id": "MAH001",
            "manufacturer_id": "MANU101",
            "raw_material_id": "RM001",
            "qty": 100,
            "unit": "kg",
            "status": "SENT_TO_MAHAJAN",
        }
    )

    try:
        governance.delete_mahajan("MAH001")
    except ValueError as exc:
        assert "active mandi supply orders" in str(exc).lower()
    else:
        raise AssertionError("Expected open-supply-order dependency to block delete.")
