from __future__ import annotations

from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.ledger_service import LedgerService
from services.pricing_service import PricingService
from services.product_catalog_service import ProductCatalogService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.domain_paths_service import DomainPathsService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import LoggingStub


def _build_stack(tmp_path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    allocator = IdAllocatorService(tmp_path / "ids.json", FileLockService())
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    governance.ensure_files()
    pricing = PricingService(
        {
            "admin_profit_share_percent": 50,
            "manufacturer_profit_share_percent": 50,
            "platform_fee_on_admin_commission": {"basic": 10, "premium": 5, "premium_plus": 1},
        }
    )
    product_catalog = ProductCatalogService(governance, allocator, pricing_service=pricing)
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    ledger = LedgerService(safe_write, json_service, allocator, DomainPathsService(drive))
    return pricing, product_catalog, governance, ledger


def test_product_supports_three_prices_and_compat_mrp(tmp_path):
    _pricing, product_catalog, governance, _ledger = _build_stack(tmp_path)
    proposed = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
        suggested_mandi_price=100,
        suggested_client_price=130,
        suggested_marketplace_price=150,
    )
    approved = product_catalog.approve_product(
        product_id=proposed["product_id"],
        approved_by="PLATFORM_ADMIN",
        approved_mandi_price=100,
        approved_client_price=130,
        approved_marketplace_price=150,
        approved_visibility="PUBLIC",
    )
    stored = governance.list_products()[0]
    assert approved["client_price"] == 130
    assert approved["marketplace_price"] == 150
    assert stored["mrp"] == 130
    assert stored["approved_mrp"] == 130


def test_price_visibility_is_role_scoped(tmp_path):
    _pricing, product_catalog, _governance, _ledger = _build_stack(tmp_path)
    proposed = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
        suggested_mandi_price=100,
        suggested_client_price=130,
        suggested_marketplace_price=150,
        visibility_request="PUBLIC",
        available_for_public_sale=True,
    )
    product_catalog.approve_product(
        product_id=proposed["product_id"],
        approved_by="PLATFORM_ADMIN",
        approved_mandi_price=100,
        approved_client_price=130,
        approved_marketplace_price=150,
        approved_visibility="PUBLIC",
    )
    manufacturer_product = product_catalog.list_products(include_pending=False, viewer_role="manufacturer", viewer_code="MANU101")[0]
    mahajan_product = product_catalog.list_products(include_pending=False, viewer_role="mahajan")[0]
    public_product = product_catalog.list_products(include_pending=False, viewer_role="public_buyer")[0]
    assert manufacturer_product["mandi_price"] == 100
    assert manufacturer_product["client_price"] == 130
    assert manufacturer_product["marketplace_price"] == 150
    assert "client_price" not in mahajan_product
    assert "marketplace_price" not in mahajan_product
    assert mahajan_product["supply_price"] == 100
    assert "mandi_price" not in public_product
    assert "client_price" not in public_product
    assert public_product["price"] == 150


def test_commission_calculates_correctly_for_subscription_plans(tmp_path):
    pricing, _product_catalog, _governance, _ledger = _build_stack(tmp_path)
    product = {"mandi_price": 100, "client_price": 130, "marketplace_price": 150}
    basic = pricing.calculate_commission(product, pricing.CHANNEL_PRIVATE_CLIENT, "basic")
    premium = pricing.calculate_commission(product, pricing.CHANNEL_PRIVATE_CLIENT, "premium")
    premium_plus = pricing.calculate_commission(product, pricing.CHANNEL_PUBLIC_MARKETPLACE, "premium_plus")
    assert basic["admin_net_commission"] == 13.5
    assert premium["admin_net_commission"] == 14.25
    assert premium_plus["admin_net_commission"] == 24.75


def test_supply_commission_tracks_spread_and_mahajan_fee(tmp_path):
    pricing, _product_catalog, _governance, _ledger = _build_stack(tmp_path)
    result = pricing.calculate_supply_commission(
        mandi_order_id="MO-2026-000001",
        mahajan_id="MAH001",
        manufacturer_id="MANU001",
        raw_material_id="RM001",
        qty=1000,
        unit="kg",
        mahajan_unit_price=35,
        manufacturer_unit_price=40,
        mahajan_fee_percent=1,
    )
    assert result["mahajan_bill_amount"] == 35000
    assert result["manufacturer_bill_amount"] == 40000
    assert result["gross_spread"] == 5000
    assert result["admin_spread_commission"] == 2500
    assert result["mahajan_transaction_fee"] == 350
    assert result["admin_total_earning"] == 2850


def test_zero_or_negative_profit_returns_zero_commission_and_warning(tmp_path):
    pricing, _product_catalog, _governance, _ledger = _build_stack(tmp_path)
    result = pricing.calculate_commission({"mandi_price": 100, "client_price": 95}, pricing.CHANNEL_PRIVATE_CLIENT, None)
    assert result["admin_net_commission"] == 0
    assert result["manufacturer_profit_share"] == 0
    assert result["pricing_warning"]
    assert result["subscription_plan"] == "basic"


def test_ledger_stores_commission_internally_and_client_view_hides_it(tmp_path):
    _pricing, _product_catalog, _governance, ledger = _build_stack(tmp_path)
    ledger.create_entry(
        "MANU101",
        party_a="MANU101",
        party_b="CLIENT101",
        entry_type="ORDER_SUPPLIED",
        amount=1300,
        paid_amount=300,
        ledger_days=10,
        note="Private client order",
        metadata={
            "channel": "PRIVATE_CLIENT",
            "mandi_price": 1000,
            "sale_price": 1300,
            "gross_profit": 300,
            "commission_breakdown": {"admin_net_commission": 135},
        },
    )
    manufacturer_view = ledger.list_ledgers_for_role("MANU101", "manufacturer")
    client_view = ledger.list_ledgers_for_role("MANU101", "client")
    assert manufacturer_view[0]["entries"][0]["metadata"]["commission_breakdown"]["admin_net_commission"] == 135
    assert "commission_breakdown" not in client_view[0]["entries"][0]["metadata"]
    assert "gross_profit" not in client_view[0]["entries"][0]["metadata"]
    assert "mandi_price" not in client_view[0]["entries"][0]["metadata"]
