from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.app_bootstrap import resolve_navigation_sections
from services.client_service import ClientService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub


def _build_persistence_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    governance.ensure_files()
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    client_service = ClientService(
        drive_service=drive,
        gmail_service=GmailStub(),
        encryption_service=EncryptionService(secret_seed="test-seed"),
        safe_drive_write_service=safe_write,
    )
    return governance, drive, client_service


def test_admin_profile_round_trip(tmp_path):
    governance, _drive, _client_service = _build_persistence_stack(tmp_path)

    saved = governance.upsert_admin_profile(
        {
            "email": "admin@example.com",
            "full_name": "Admin User",
            "mobile": "9876543210",
            "designation": "Platform Admin",
            "address": {"city": "Pune", "state": "Maharashtra", "pin_code": "411001"},
            "support_email": "support@example.com",
            "notification_email": "alerts@example.com",
            "credential_reference": "Stored in Streamlit secrets",
        }
    )

    fetched = governance.get_admin_profile("admin@example.com")
    assert saved["email"] == "admin@example.com"
    assert fetched is not None
    assert fetched["support_email"] == "support@example.com"
    assert fetched["address"]["city"] == "Pune"


def test_client_profile_upsert_persists_delivery_details(tmp_path):
    _governance, drive, client_service = _build_persistence_stack(tmp_path)
    drive.initialize_manufacturer_workspace("MANU101", "Shree Agro Traders", owner_email="owner@example.com", city="Pune")
    client_service.create_invite("MANU101", "buyer@example.com", "Kumar Traders")
    client_service.complete_profile(
        "MANU101",
        {
            "client_id": "CLIENT101",
            "manufacturer_id": "MANU101",
            "business_name": "Kumar Traders",
            "owner_name": "Amit Kumar",
            "email": "buyer@example.com",
        },
    )

    updated = client_service.upsert_client_profile(
        "MANU101",
        "buyer@example.com",
        {
            "mobile": "9999999999",
            "alternate_mobile": "8888888888",
            "address": {
                "line1": "Shop 42, Grain Market",
                "city": "Pune",
                "state": "Maharashtra",
                "pin_code": "411001",
                "landmark": "Near APMC Gate",
            },
            "delivery_contact": {"name": "Amit Kumar", "mobile": "9999999999"},
            "delivery_instructions": "Call before dispatch arrival.",
        },
    )

    assert updated["address"]["line1"] == "Shop 42, Grain Market"
    assert updated["address"]["landmark"] == "Near APMC Gate"
    assert updated["delivery_instructions"] == "Call before dispatch arrival."


def test_navigation_sections_include_my_profile_for_signed_in_roles():
    security_service = SimpleNamespace(is_admin_identity=lambda user: user.role == "platform_admin")
    worker_service = SimpleNamespace(get_worker_by_email=lambda _email: None)

    admin_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )
    manufacturer_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101"),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )
    client_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="client", email="buyer@example.com", manufacturer_code="MANU101"),
            "security_service": security_service,
            "worker_service": worker_service,
        }
    )

    assert "My Profile" in admin_sections
    assert "My Profile" in manufacturer_sections
    assert "My Profile" in client_sections
