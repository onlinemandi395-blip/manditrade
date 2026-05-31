from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.client_service import ClientService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.access_portal_service import AccessPortalService
from services.id_allocator_service import IdAllocatorService
from services.ledger_service import LedgerService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub
from services.query.order_query_service import OrderQueryService


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
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    governance.ensure_files()
    gmail = GmailStub()
    client_service = ClientService(
        drive_service=drive,
        gmail_service=gmail,
        encryption_service=EncryptionService(secret_seed="test-seed"),
        safe_drive_write_service=safe_write,
        logging_service=LoggingStub(),
    )
    access_service = AccessPortalService(
        governance_root=tmp_path / "governance",
        safe_drive_write_service=safe_write,
        governance_service=governance,
        client_service=client_service,
        worker_service=SimpleNamespace(get_worker_by_email=lambda _email: None, upsert_worker=lambda **_kwargs: None),
        public_buyer_service=SimpleNamespace(get_by_email=lambda _email: None, register_or_get=lambda **_kwargs: {"status": "ACTIVE"}),
        drive_service=drive,
        security_service=SimpleNamespace(get_admin_email=lambda: None),
        json_service=json_service,
    )
    return governance, drive, client_service, gmail, access_service


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


def test_client_create_edit_and_privacy_are_scoped_by_manufacturer(tmp_path):
    governance, drive, client_service, _gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    _seed_manufacturer(governance, drive, "MANU202", "owner2@example.com")

    created = client_service.create_client(
        "MANU101",
        {
            "business_name": "Kumar Traders",
            "owner_name": "Amit Kumar",
            "email": "buyer@example.com",
            "address": {"city": "Pune", "state": "Maharashtra"},
        },
    )
    updated = client_service.update_client("MANU101", created["client_id"], {"mobile": "9999999999", "status": "ACTIVE"})

    assert updated["mobile"] == "9999999999"
    assert client_service.get_client("MANU202", created["client_id"]) is None
    with pytest.raises(ValueError, match="Client not found"):
        client_service.update_client("MANU202", created["client_id"], {"mobile": "8888888888"})


def test_client_invite_gmail_is_triggered_and_status_updates(tmp_path):
    governance, drive, client_service, gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    invite = client_service.create_invite("MANU101", "buyer@example.com", "Kumar Traders", owner_name="Amit Kumar")

    sent = client_service.send_invitation("MANU101", invite["client_id"], "MANU101 Traders", "https://manditrade.example/login")

    assert gmail.sent[0]["notification_type"] == "client_invited"
    assert sent["invite_status"] == "SENT"
    assert sent["status"] == "INVITED"


def test_client_sign_in_maps_to_manufacturer_and_activates_profile(tmp_path):
    governance, drive, client_service, _gmail, access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    invite = client_service.create_invite("MANU101", "buyer@example.com", "Kumar Traders", owner_name="Amit Kumar")

    request = access_service.submit_signup_request(
        requested_role="client",
        email="buyer@example.com",
        full_name="Amit Kumar",
        manufacturer_code="MANU101",
        invite_token=invite["onboarding_token"],
        business_name="Kumar Traders",
        city="Pune",
    )
    resolved = access_service.resolve_identity(
        email="buyer@example.com",
        display_name="Amit Kumar",
        preferred_role="client",
        manufacturer_code="MANU101",
    )
    profile = client_service.get_client_profile_by_email("MANU101", "buyer@example.com")
    stored = client_service.get_client_by_email("MANU101", "buyer@example.com")

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "client"
    assert resolved["manufacturer_code"] == "MANU101"
    assert profile is not None
    assert stored["status"] == "ACTIVE"
    assert stored["invite_status"] == "ACCEPTED"


def test_superadmin_summary_helpers_hide_private_client_and_ledger_data(tmp_path):
    governance, drive, client_service, _gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    client = client_service.create_client(
        "MANU101",
        {
            "business_name": "Kumar Traders",
            "owner_name": "Amit Kumar",
            "email": "buyer@example.com",
            "address": {"line1": "Shop 7", "city": "Pune", "state": "Maharashtra"},
            "status": "ACTIVE",
        },
    )
    order_path = drive.get_manufacturer_paths("MANU101").private_zone / "client_orders" / "ORD-2026-000001.json"
    json_service = JsonServiceStub()
    order_query = OrderQueryService(drive, json_service)
    json_service.write_json(
        order_path,
        {
            "order_id": "ORD-2026-000001",
            "client_email": "buyer@example.com",
            "shipping_address": {"line1": "Secret Address"},
            "negotiation_comments": ["private"],
            "status": "CONFIRMED",
            "grand_total": 1250,
        },
    )
    ledger_service = LedgerService(
        safe_drive_write_service=drive.safe_drive_write_service,
        json_service=json_service,
        id_allocator_service=IdAllocatorService(tmp_path / "id_counters.json", FileLockService()),
        domain_paths_service=type("Paths", (), {"ledger_path": lambda self, code: drive.get_manufacturer_paths(code).shared_zone / "ledgers.json"})(),
    )
    ledger_service.create_entry(
        "MANU101",
        party_a="MANU101",
        party_b=client["client_id"],
        entry_type="ORDER_SUPPLIED",
        amount=1250,
        paid_amount=250,
        ledger_days=10,
        note="Private collection note",
    )

    client_summary = client_service.summarize_clients("MANU101")
    order_summary = order_query.summarize_orders("MANU101")
    ledger_summary = ledger_service.summarize_ledgers("MANU101")

    assert client_summary["total_clients"] == 1
    assert "buyer@example.com" not in str(client_summary)
    assert "Amit Kumar" not in str(client_summary)
    assert order_summary["total_orders"] == 1
    assert "Secret Address" not in str(order_summary)
    assert "private" not in str(order_summary)
    assert ledger_summary["total_entries"] == 1
    assert "Private collection note" not in str(ledger_summary)


def test_private_client_order_stays_out_of_shared_projection(tmp_path):
    governance, drive, client_service, _gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    private_order = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000001",
        "client_id": "CLIENT101",
        "client_email": "buyer@example.com",
        "shipping_address": {"line1": "Private Street"},
        "payment_proposal": {"freestyle_note": "Private note"},
        "items": [{"product_id": "PRD-1", "qty": 10, "client_price": 50}],
        "status": "PROPOSED",
        "created_at": "2026-05-30",
    }
    shared_projection = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000001",
        "item_count": 1,
        "total_amount": 500,
        "status": "PROPOSED",
        "items": [{"product_id": "PRD-1", "qty": 10}],
    }
    drive.json_service.write_json(drive.get_manufacturer_paths("MANU101").private_zone / "client_orders" / "ORD-2026-000001.json", private_order)
    drive.json_service.write_json(drive.resolve_orders_month_dir("MANU101", "2026-05") / "ORD-2026-000001.json", shared_projection)

    stored_private = drive.json_service.read_json(drive.get_manufacturer_paths("MANU101").private_zone / "client_orders" / "ORD-2026-000001.json", {})
    stored_shared = drive.json_service.read_json(drive.resolve_orders_month_dir("MANU101", "2026-05") / "ORD-2026-000001.json", {})

    assert stored_private["shipping_address"]["line1"] == "Private Street"
    assert "shipping_address" not in stored_shared
    assert "payment_proposal" not in stored_shared


def test_other_manufacturer_cannot_read_private_order_registry(tmp_path):
    governance, drive, _client_service, _gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "MANU101", "owner1@example.com")
    _seed_manufacturer(governance, drive, "MANU202", "owner2@example.com")
    private_order = {
        "schema_version": "2.0",
        "order_id": "ORD-2026-000001",
        "client_id": "CLIENT101",
        "client_email": "buyer@example.com",
        "items": [{"product_id": "PRD-1", "qty": 10, "client_price": 50}],
        "status": "PROPOSED",
        "created_at": "2026-05-30",
    }
    drive.json_service.write_json(drive.get_manufacturer_paths("MANU101").private_zone / "client_orders" / "ORD-2026-000001.json", private_order)
    order_query = OrderQueryService(drive, drive.json_service)

    assert order_query.get_order("MANU101", "ORD-2026-000001") is not None
    assert order_query.get_order("MANU202", "ORD-2026-000001") is None


def test_superuser_admin_manu_context_can_see_only_admin_manu_private_clients(tmp_path):
    governance, drive, client_service, _gmail, _access_service = _build_stack(tmp_path)
    _seed_manufacturer(governance, drive, "ADMIN_MANU", "admin@example.com")
    _seed_manufacturer(governance, drive, "MANU202", "owner2@example.com")
    admin_client = client_service.create_client(
        "ADMIN_MANU",
        {
            "business_name": "Admin Retail",
            "owner_name": "Admin Operator",
            "email": "admin-client@example.com",
            "status": "ACTIVE",
        },
    )
    other_client = client_service.create_client(
        "MANU202",
        {
            "business_name": "Other Retail",
            "owner_name": "Other Owner",
            "email": "other-client@example.com",
            "status": "ACTIVE",
        },
    )

    admin_clients = client_service.list_clients("ADMIN_MANU")
    assert any(item.get("email") == admin_client["email"] for item in admin_clients)
    assert all(item.get("email") != other_client["email"] for item in admin_clients)
