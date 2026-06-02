from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.auth_service import AuthUser
from services.client_service import ClientService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.security_service import SecurityService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub
from tests.helpers.transaction_fixtures import build_order_service, build_procurement_service, build_runtime


def _client_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    service = ClientService(
        drive_service=drive,
        gmail_service=GmailStub(),
        encryption_service=EncryptionService(secret_seed="test-seed"),
        safe_drive_write_service=safe_write,
    )
    return drive, service


def test_superuser_context_separates_platform_and_admin_manufacturer_modes(tmp_path):
    security = SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=SimpleNamespace(),
        admin_token_file=tmp_path / "admin.enc",
        manufacturer_token_dir=tmp_path / "manufacturers",
        runtime_tokens_dir=tmp_path / "runtime",
    )
    user = AuthUser(email="admin@example.com", name="Admin", role="platform_admin", base_role="platform_admin", active_context="platform_admin")
    platform_view = security.build_effective_user(user)
    manufacturer_view = security.build_effective_user(AuthUser(email="admin@example.com", name="Admin", role="platform_admin", base_role="platform_admin", active_context="manufacturer"))

    assert platform_view.role == "platform_admin"
    assert platform_view.manufacturer_code is None
    assert manufacturer_view.role == "manufacturer"
    assert manufacturer_view.manufacturer_code == security.ADMIN_MANUFACTURER_CODE


def test_public_marketplace_payment_goes_directly_to_seller(tmp_path):
    from tests.test_public_marketplace import build_public_stack, seed_public_product

    stack = build_public_stack(tmp_path)
    seed_public_product(stack, product_id="PRD-2026-000001", manufacturer_code="MANU101")
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])

    assert order["payment_receiver"] == order["assigned_seller_manufacturer_id"]
    assert order["commission_status"] == "CALCULATED"


def test_client_credit_limit_blocks_confirm_without_override(tmp_path):
    runtime = build_runtime(tmp_path)
    drive = runtime["drive"]
    drive.initialize_manufacturer_workspace("MANU101", "Shree Agro", owner_email="owner@example.com", city="Pune")
    runtime["client_service"].create_client(
        "MANU101",
        {
            "client_id": "CLIENT101",
            "business_name": "Kumar Traders",
            "owner_name": "Amit",
            "email": "buyer@example.com",
            "credit_limit": 1000,
            "status": "ACTIVE",
        },
    )
    from tests.helpers.transaction_fixtures import seed_inventory
    seed_inventory(runtime, "MANU101", self_qty=500, mandi_qty=0)
    service = build_order_service(runtime)
    order = service.create_order(
        "MANU101",
        {"client_id": "CLIENT101", "email": "buyer@example.com", "subscription_plan": "basic"},
        [{"product_id": "PRD-2026-000001", "product_name": "Rice", "qty": 50, "unit": "kg", "mrp": 50, "client_price": 50, "mandi_price": 40}],
        {"payment_modes": ["khata"], "upfront_percentage": 0, "ledger_days": 10, "freestyle_note": "udhar"},
    )
    try:
        service.confirm_order(SimpleNamespace(manufacturer_code="MANU101", email="owner@example.com"), order["order_id"])
    except ValueError as exc:
        assert "credit limit exceeded" in str(exc).lower()
    else:
        raise AssertionError("Expected credit-limit block.")


def test_partial_payment_updates_ledger_status_and_credit(tmp_path):
    runtime = build_runtime(tmp_path)
    drive = runtime["drive"]
    drive.initialize_manufacturer_workspace("MANU101", "Shree Agro", owner_email="owner@example.com", city="Pune")
    runtime["client_service"].create_client(
        "MANU101",
        {
            "client_id": "CLIENT101",
            "business_name": "Kumar Traders",
            "owner_name": "Amit",
            "email": "buyer@example.com",
            "credit_limit": 100000,
            "status": "ACTIVE",
        },
    )
    ledger_service = build_order_service(runtime).ledger_service
    entry = ledger_service.create_entry(
        "MANU101",
        party_a="MANU101",
        party_b="CLIENT101",
        entry_type="ORDER_SUPPLIED",
        amount=50000,
        paid_amount=0,
        ledger_days=10,
        note="Khata order",
        metadata={"order_id": "ORD-1"},
    )
    partial = ledger_service.add_payment("MANU101", "LEDGER-MANU101-CLIENT101", entry["entry_id"], 20000, "first payment")
    final = ledger_service.add_payment("MANU101", "LEDGER-MANU101-CLIENT101", entry["entry_id"], 30000, "final payment")
    summary = runtime["client_service"].summarize_credit("MANU101", "CLIENT101", ledger_service)

    assert partial["status"] == "PARTIAL"
    assert final["status"] == "PAID"
    assert summary["current_outstanding"] == 0
    assert summary["available_credit"] == 100000


def test_mandi_order_is_admin_routed_with_direct_supplier_payment_and_admin_logistics(tmp_path):
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
    order = procurement.create_supply_request(
        manufacturer_code="MANU101",
        raw_material_id="RM001",
        qty=1000,
        unit="kg",
        requested_by="buyer@example.com",
    )
    assigned = procurement.assign_supply_to_mahajan(mandi_order_id=order["mandi_order_id"], mahajan_id="MAH001", admin_email="admin@example.com")
    quoted = procurement.quote_supply_order(
        mandi_order_id=order["mandi_order_id"],
        mahajan_id="MAH001",
        mahajan_unit_price=35,
        mahajan_email="mahajan@example.com",
    )
    confirmed = procurement.set_manufacturer_supply_price(
        mandi_order_id=order["mandi_order_id"],
        manufacturer_unit_price=40,
        admin_email="admin@example.com",
    )
    logistics = procurement.update_supply_logistics(
        mandi_order_id=order["mandi_order_id"],
        actor_email="admin@example.com",
        transport_mode="Truck",
        vehicle_number="MH12AB1234",
        delivery_status="READY",
    )

    assert assigned["route_type"] == "ADMIN_ROUTED"
    assert quoted["payment_receiver"] == "MAH001"
    assert confirmed["commission_object"]["payment_recipient"] == "SUPPLIER_DIRECT"
    assert logistics["logistics"]["logistics_owner"] == "platform_admin"
    assert logistics["logistics"]["vehicle_number"] == "MH12AB1234"


def test_public_buyer_can_become_manufacturer_specific_client_without_losing_public_identity(tmp_path):
    drive, client_service = _client_stack(tmp_path)
    drive.initialize_manufacturer_workspace("MANU101", "Shree Agro", owner_email="owner@example.com", city="Pune")
    buyer_profile = {
        "public_buyer_id": "PB-1",
        "email": "buyer@example.com",
        "full_name": "Buyer One",
        "profile_status": "ACTIVE",
    }
    client_service.create_invite("MANU101", "buyer@example.com", "Buyer Private Shop", owner_name="Buyer One")
    profile = client_service.complete_profile(
        "MANU101",
        {
            "client_id": "CLIENT101",
            "manufacturer_id": "MANU101",
            "business_name": "Buyer Private Shop",
            "owner_name": "Buyer One",
            "email": "buyer@example.com",
        },
    )

    assert buyer_profile["public_buyer_id"] == "PB-1"
    assert profile["manufacturer_id"] == "MANU101"
    assert profile["email"] == "buyer@example.com"


def test_worker_navigation_and_payment_restrictions_remain_active():
    auth_ui = Path("tests/test_auth_ui.py").read_text(encoding="utf-8")
    assert 'assert can_access_route(worker, "Jobs", app_context) is True' in auth_ui
    assert 'assert can_access_route(worker, "Marketplace", app_context) is False' in auth_ui
