from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.access_portal_service import AccessPortalService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.public_buyer_service import PublicBuyerService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.query.order_query_service import OrderQueryService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import LoggingStub


def _build_stack(tmp_path: Path):
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
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    governance.ensure_files()
    public_buyer_service = PublicBuyerService(
        public_buyers_root=tmp_path / "public_buyers",
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=type("Allocator", (), {"allocate": lambda self, domain: "PB-2026-000001"})(),
    )
    access_service = AccessPortalService(
        governance_root=tmp_path / "governance",
        safe_drive_write_service=safe_write,
        governance_service=governance,
        worker_service=SimpleNamespace(get_worker_by_email=lambda _email: None, upsert_worker=lambda **_kwargs: None),
        public_buyer_service=public_buyer_service,
        drive_service=drive,
        security_service=SimpleNamespace(get_admin_email=lambda: None),
        json_service=json_service,
    )
    return governance, drive, public_buyer_service, access_service


def _seed_manufacturer(governance, drive, manufacturer_code: str, owner_email: str):
    drive.initialize_manufacturer_workspace(manufacturer_code, f"{manufacturer_code} Traders", owner_email=owner_email, city="Pune")
    governance.register_manufacturer(
        {
            "manufacturer_id": f"{manufacturer_code}-ID",
            "manufacturer_code": manufacturer_code,
            "manufacturer_name": f"{manufacturer_code} Traders",
            "business_name": f"{manufacturer_code} Traders",
            "owner_name": "Owner",
            "owner_email": owner_email,
            "status": "ACTIVE",
        }
    )


def test_public_buyer_signup_stays_separate_from_manufacturer_workspace(tmp_path):
    governance, drive, public_buyer_service, access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")

    request = access_service.submit_signup_request(
        requested_role="public_buyer",
        email="buyer@example.com",
        full_name="Amit Kumar",
        city="Pune",
    )
    resolved = access_service.resolve_identity(
        email="buyer@example.com",
        display_name="Amit Kumar",
        preferred_role="public_buyer",
        manufacturer_code="MANU101",
    )
    buyer = public_buyer_service.get_by_email("buyer@example.com")

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "public_buyer"
    assert resolved["manufacturer_code"] is None
    assert buyer is not None


def test_mahajan_identity_activates_after_admin_review(tmp_path):
    governance, _drive, _public_buyer_service, access_service = _build_stack(tmp_path)
    governance.upsert_mahajan(
        {
            "mahajan_id": "MHJ-2026-000001",
            "name": "Supply Partner",
            "email": "mahajan@example.com",
            "mobile": "9999999999",
            "status": "INVITED",
        }
    )

    request = access_service.submit_signup_request(
        requested_role="mahajan",
        email="mahajan@example.com",
        full_name="Supply Partner",
    )
    access_service._mark_request_status(request["request_id"], "READY_FOR_GOOGLE_SIGNIN")  # noqa: SLF001
    resolved = access_service.resolve_identity(
        email="mahajan@example.com",
        display_name="Supply Partner",
        preferred_role="mahajan",
    )

    assert resolved["role"] == "mahajan"
    assert resolved["status"] == "ACTIVE"


def test_marketplace_order_registry_stays_scoped_by_manufacturer(tmp_path):
    governance, drive, _public_buyer_service, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    _seed_manufacturer(governance, drive, "MANU202", "owner2@example.com")

    order = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000001",
        "assigned_seller_manufacturer_id": "MANU101",
        "shipping_address": {"line1": "Private Street"},
        "payment_reference": "UTR12345",
        "items": [{"product_id": "PRD-1", "qty": 10, "marketplace_price": 50}],
        "status": "PAID",
        "created_at": "2026-05-30",
    }
    drive.json_service.write_json(drive.get_manufacturer_paths("MANU101").private_zone / "client_orders" / "ORD-2026-000001.json", order)
    order_query = OrderQueryService(drive, drive.json_service)

    assert order_query.get_order("MANU101", "ORD-2026-000001") is not None
    assert order_query.get_order("MANU202", "ORD-2026-000001") is None


def test_superuser_admin_manu_context_stays_scoped_to_admin_manu_workspace(tmp_path):
    governance, drive, _public_buyer_service, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "ADMIN_MANU", "admin@example.com")
    _seed_manufacturer(governance, drive, "MANU202", "owner2@example.com")

    admin_order = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000001",
        "assigned_seller_manufacturer_id": "ADMIN_MANU",
        "items": [{"product_id": "PRD-1", "qty": 2, "marketplace_price": 120}],
        "status": "PAID",
        "created_at": "2026-05-30",
    }
    other_order = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000002",
        "assigned_seller_manufacturer_id": "MANU202",
        "items": [{"product_id": "PRD-2", "qty": 4, "marketplace_price": 80}],
        "status": "PAID",
        "created_at": "2026-05-30",
    }
    drive.json_service.write_json(drive.get_manufacturer_paths("ADMIN_MANU").private_zone / "client_orders" / "ORD-2026-000001.json", admin_order)
    drive.json_service.write_json(drive.get_manufacturer_paths("MANU202").private_zone / "client_orders" / "ORD-2026-000002.json", other_order)
    order_query = OrderQueryService(drive, drive.json_service)

    admin_orders = order_query.list_orders("ADMIN_MANU")
    assert [item["order_id"] for item in admin_orders] == ["ORD-2026-000001"]
