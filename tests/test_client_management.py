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
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub


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
