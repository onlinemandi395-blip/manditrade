from __future__ import annotations

from pathlib import Path

from services.access_portal_service import AccessPortalService
from services.auth_service import AuthService
from services.client_service import ClientService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.public_buyer_service import PublicBuyerService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.security_service import SecurityService
from services.worker_service import WorkerService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub


def _oauth_config() -> dict:
    return {
        "google_oauth": {
            "client_id": "client-id",
            "client_secret": "client-secret",
            "redirect_uri": "https://example.streamlit.app",
            "project_id": "project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["openid"],
        }
    }


def build_access_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    governance_root = tmp_path / "governance"
    drive_service = DriveStub(tmp_path / "manufacturers", json_service)
    drive_service.safe_drive_write_service = safe_write
    governance_service = GovernanceService(governance_root, safe_write)
    governance_service.ensure_files()
    client_service = ClientService(
        drive_service=drive_service,
        gmail_service=GmailStub(),
        encryption_service=EncryptionService(secret_seed="test-seed"),
        safe_drive_write_service=safe_write,
    )
    worker_service = WorkerService(governance_root, safe_write, json_service, id_allocator_service=type("Allocator", (), {"allocate": lambda self, domain: "WRK-2026-000001"})())
    public_buyer_service = PublicBuyerService(
        public_buyers_root=tmp_path / "public_buyers",
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=type("Allocator", (), {"allocate": lambda self, domain: "PB-2026-000001"})(),
    )
    auth_service = AuthService(_oauth_config(), enable_mock_auth=False)
    security_service = SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=auth_service,
        admin_token_file=tmp_path / "admin.enc",
        manufacturer_token_dir=tmp_path / "manufacturer_tokens",
        runtime_tokens_dir=tmp_path / "runtime_tokens",
        require_verification_for_admin_runtime=False,
    )
    security_service.get_admin_email = lambda: None  # type: ignore[method-assign]
    access_portal_service = AccessPortalService(
        governance_root=governance_root,
        safe_drive_write_service=safe_write,
        governance_service=governance_service,
        client_service=client_service,
        worker_service=worker_service,
        public_buyer_service=public_buyer_service,
        drive_service=drive_service,
        security_service=security_service,
        json_service=json_service,
    )
    return governance_service, drive_service, client_service, worker_service, public_buyer_service, access_portal_service


def test_manufacturer_signup_request_validates_onboarding_packet(tmp_path):
    governance_service, drive_service, _client_service, _worker_service, _public_buyer_service, access_portal_service = build_access_stack(tmp_path)
    drive_service.initialize_manufacturer_workspace("MANU101", "Shree Agro Traders", owner_email="", city="Pune")
    governance_service.register_manufacturer(
        {
            "manufacturer_code": "MANU101",
            "manufacturer_name": "Shree Agro Traders",
            "owner_email": "",
            "city": "Pune",
            "status": "ACTIVE",
            "manufacturer_onboarding_secret": "MANU-SETUP-SECRET",
        }
    )

    request = access_portal_service.submit_signup_request(
        requested_role="manufacturer",
        email="owner@example.com",
        full_name="Owner User",
        manufacturer_code="MANU101",
        onboarding_secret="MANU-SETUP-SECRET",
        city="Pune",
    )
    resolved = access_portal_service.resolve_identity(
        email="owner@example.com",
        display_name="Owner User",
        preferred_role="manufacturer",
        manufacturer_code="MANU101",
    )

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "manufacturer"
    assert resolved["manufacturer_code"] == "MANU101"
    assert resolved["status"] == "ACTIVE"


def test_client_signup_request_activates_profile_on_first_google_login(tmp_path):
    governance_service, drive_service, client_service, _worker_service, _public_buyer_service, access_portal_service = build_access_stack(tmp_path)
    drive_service.initialize_manufacturer_workspace("MANU101", "Shree Agro Traders", owner_email="owner@example.com", city="Pune")
    governance_service.register_manufacturer(
        {
            "manufacturer_code": "MANU101",
            "manufacturer_name": "Shree Agro Traders",
            "owner_email": "owner@example.com",
            "city": "Pune",
            "status": "ACTIVE",
        }
    )
    invite = client_service.create_invite("MANU101", "buyer@example.com", "Kumar Traders")

    request = access_portal_service.submit_signup_request(
        requested_role="client",
        email="buyer@example.com",
        full_name="Amit Kumar",
        manufacturer_code="MANU101",
        invite_token=invite["onboarding_token"],
        manufacturer_name="Kumar Traders",
        city="Pune",
    )
    resolved = access_portal_service.resolve_identity(
        email="buyer@example.com",
        display_name="Amit Kumar",
        preferred_role="client",
        manufacturer_code="MANU101",
    )

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "client"
    assert client_service.list_client_profiles("MANU101")[0]["email"] == "buyer@example.com"


def test_worker_signup_request_creates_worker_dashboard_identity(tmp_path):
    _governance_service, _drive_service, _client_service, worker_service, _public_buyer_service, access_portal_service = build_access_stack(tmp_path)

    request = access_portal_service.submit_signup_request(
        requested_role="worker",
        email="worker@example.com",
        full_name="Ravi Kumar",
        city="Pune",
        mobile="9999999999",
        area="Bhosari",
        skills=["Loading", "Packaging"],
        preferred_work_type=["Daily Wage", "Part-time"],
    )
    resolved = access_portal_service.resolve_identity(
        email="worker@example.com",
        display_name="Ravi Kumar",
        preferred_role="worker",
    )
    worker = worker_service.get_worker_by_email("worker@example.com")

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "worker"
    assert worker is not None
    assert worker["skills"] == ["Loading", "Packaging"]


def test_public_buyer_signup_creates_public_marketplace_identity(tmp_path):
    _governance_service, _drive_service, _client_service, _worker_service, public_buyer_service, access_portal_service = build_access_stack(tmp_path)

    request = access_portal_service.submit_signup_request(
        requested_role="public_buyer",
        email="shopper@example.com",
        full_name="Public Shopper",
    )
    resolved = access_portal_service.resolve_identity(
        email="shopper@example.com",
        display_name="Public Shopper",
        preferred_role="public_buyer",
    )
    buyer = public_buyer_service.get_by_email("shopper@example.com")

    assert request["status"] == "READY_FOR_GOOGLE_SIGNIN"
    assert resolved["role"] == "public_buyer"
    assert buyer is not None
    assert buyer["status"] == "ACTIVE"
