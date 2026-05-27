from __future__ import annotations

from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.manufacturer_onboarding_service import ManufacturerOnboardingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import LoggingStub


def _build_service(tmp_path):
    json_service = JsonServiceStub()
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
    return ManufacturerOnboardingService(drive, governance, safe_write, json_service), governance, drive


def test_admin_can_create_manufacturer_onboarding_packet(tmp_path):
    service, governance, drive = _build_service(tmp_path)
    manufacturer = service.create_manufacturer(
        manufacturer_code="manu101",
        manufacturer_name="Shree Agro Traders",
        owner_email="owner@example.com",
        city="Jaipur",
        created_by="admin@example.com",
    )
    stored = governance.get_manufacturer("MANU101")
    config = drive.json_service.read_json(drive.get_manufacturer_paths("MANU101").private_zone / "manufacturer_config.json", {})
    assert manufacturer["manufacturer_code"] == "MANU101"
    assert "manufacturer_onboarding_secret" in stored
    assert "Share your first-time manufacturer onboarding secret with admin" in stored["manufacturer_onboarding_steps"]
    assert config["manufacturer_onboarding_secret"] == stored["manufacturer_onboarding_secret"]


def test_admin_can_regenerate_secret_and_update_packet(tmp_path):
    service, governance, _drive = _build_service(tmp_path)
    created = service.create_manufacturer(
        manufacturer_code="MANU101",
        manufacturer_name="Shree Agro Traders",
        owner_email="owner@example.com",
        city="Jaipur",
        created_by="admin@example.com",
    )
    refreshed = service.regenerate_secret("MANU101")
    assert refreshed["manufacturer_onboarding_secret"] != created["manufacturer_onboarding_secret"]
    assert refreshed["manufacturer_onboarding_secret"] in refreshed["manufacturer_onboarding_steps"]
