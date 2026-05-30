from __future__ import annotations

import pytest

from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.manufacturer_onboarding_service import ManufacturerOnboardingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import LoggingStub


def _build_service(tmp_path):
    json_service = JsonServiceStub()
    id_allocator = IdAllocatorService(tmp_path / "ids.json", FileLockService())
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "version_history",
    )
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    return ManufacturerOnboardingService(drive, governance, safe_write, json_service, id_allocator_service=id_allocator), governance, drive


def test_admin_can_create_manufacturer_onboarding_packet(tmp_path):
    service, governance, drive = _build_service(tmp_path)
    manufacturer = service.create_manufacturer(
        manufacturer_name="Shree Agro Traders",
        owner_name="Ramesh Kumar",
        owner_email="owner@example.com",
        mobile="9876543210",
        city="Jaipur",
        state="Rajasthan",
        pin_code="302001",
        created_by="admin@example.com",
    )
    stored = governance.get_manufacturer("MANU001")
    config = drive.json_service.read_json(drive.get_manufacturer_paths("MANU001").private_zone / "manufacturer_config.json", {})
    assert manufacturer["status"] == "ACTIVE"
    assert manufacturer["banking"]["ifsc"] == ""
    assert "manufacturer_onboarding_secret" in stored
    assert "Share your first-time manufacturer onboarding secret with admin" in stored["manufacturer_onboarding_steps"]
    assert config["manufacturer_onboarding_secret"] == stored["manufacturer_onboarding_secret"]
    assert config["business_name"] == "Shree Agro Traders"
    assert config["status"] == "ACTIVE"
    assert manufacturer["manufacturer_code"] == "MANU001"


def test_admin_can_regenerate_secret_and_update_packet(tmp_path):
    service, governance, _drive = _build_service(tmp_path)
    created = service.create_manufacturer(
        manufacturer_code="MANU101",
        manufacturer_name="Shree Agro Traders",
        owner_name="Ramesh Kumar",
        owner_email="owner@example.com",
        mobile="9876543210",
        city="Jaipur",
        state="Rajasthan",
        pin_code="302001",
        created_by="admin@example.com",
    )
    refreshed = service.regenerate_secret("MANU101")
    assert refreshed["manufacturer_onboarding_secret"] != created["manufacturer_onboarding_secret"]
    assert refreshed["manufacturer_onboarding_secret"] in refreshed["manufacturer_onboarding_steps"]


def test_manufacturer_code_generation_increments_and_skips_legacy_codes(tmp_path):
    service, governance, _drive = _build_service(tmp_path)
    first = service.create_manufacturer(
        manufacturer_name="Alpha Traders",
        owner_name="A One",
        owner_email="alpha@example.com",
        mobile="9876543210",
        city="Jaipur",
        state="Rajasthan",
        pin_code="302001",
        created_by="admin@example.com",
    )
    governance.register_manufacturer(
        {
            "manufacturer_id": "MANU-2026-999999",
            "manufacturer_code": "MANU-2026-000001",
            "business_name": "Legacy Co",
            "manufacturer_name": "Legacy Co",
            "owner_name": "Legacy Owner",
            "owner_email": "legacy@example.com",
        }
    )
    second = service.create_manufacturer(
        manufacturer_name="Beta Traders",
        owner_name="B One",
        owner_email="beta@example.com",
        mobile="9876543211",
        city="Jaipur",
        state="Rajasthan",
        pin_code="302001",
        created_by="admin@example.com",
    )
    assert first["manufacturer_code"] == "MANU001"
    assert second["manufacturer_code"] == "MANU002"


def test_duplicate_manufacturer_code_is_blocked(tmp_path):
    service, _governance, _drive = _build_service(tmp_path)
    service.create_manufacturer(
        manufacturer_code="MANU050",
        manufacturer_name="Original",
        owner_name="Owner One",
        owner_email="one@example.com",
        mobile="9876543210",
        city="Jaipur",
        state="Rajasthan",
        pin_code="302001",
        created_by="admin@example.com",
    )
    with pytest.raises(ValueError, match="Manufacturer code already exists"):
        service.create_manufacturer(
            manufacturer_code="MANU050",
            manufacturer_name="Duplicate",
            owner_name="Owner Two",
            owner_email="two@example.com",
            mobile="9876543211",
            city="Jaipur",
            state="Rajasthan",
            pin_code="302001",
            created_by="admin@example.com",
        )


@pytest.mark.parametrize(
    ("field_overrides", "message"),
    [
        ({"mobile": "12345"}, "Mobile Number must be 10 digits."),
        ({"pin_code": "123"}, "PIN Code must be 6 digits."),
        ({"gstin": "SHORT"}, "GSTIN must be 15 characters if provided."),
        ({"pan": "SHORT"}, "PAN Number must be 10 characters if provided."),
        ({"aadhaar": "1234"}, "Aadhaar Number must be 12 digits if provided."),
        ({"ifsc_code": "SHORT"}, "IFSC Code must be 11 characters if provided."),
    ],
)
def test_manufacturer_validation_rules(tmp_path, field_overrides, message):
    service, _governance, _drive = _build_service(tmp_path)
    payload = {
        "manufacturer_code": "MANU101",
        "manufacturer_name": "Shree Agro Traders",
        "owner_name": "Ramesh Kumar",
        "owner_email": "owner@example.com",
        "mobile": "9876543210",
        "city": "Jaipur",
        "state": "Rajasthan",
        "pin_code": "302001",
        "created_by": "admin@example.com",
    }
    payload.update(field_overrides)
    with pytest.raises(ValueError, match=message):
        service.create_manufacturer(**payload)
