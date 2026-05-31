from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.route_registry import render_route
from bootstrap.app_bootstrap import resolve_navigation_sections
from services.navigation_service import ROLE_NAVIGATION_MAP
from services.auth_service import AuthUser
from services.security_service import SecurityService
from services.client_service import ClientService
from services.encryption_service import EncryptionService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.master_data_service import MasterDataService
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

    assert admin_sections == [
        "My Profile",
        "Dashboard",
        "Notifications",
        "My Actions",
        "Manufacturers",
        "Products",
        "Product Approvals",
        "Marketplace",
        "Marketplace Orders",
        "Mandi Network",
        "Mandi Orders",
        "RFQ",
        "Jobs",
        "Platform Commission",
        "Payments",
        "Ledger",
        "System Health",
    ]
    assert manufacturer_sections == [
        "My Profile",
        "Dashboard",
        "Notifications",
        "My Actions",
        "Products",
        "Product Approvals",
        "Clients",
        "Mandi Network",
        "Mandi Orders",
        "RFQ",
        "Jobs",
        "Platform Commission",
        "Payments",
        "Ledger",
    ]
    assert client_sections == [
        "My Profile",
        "Dashboard",
        "Notifications",
        "My Actions",
        "Marketplace",
        "Marketplace Orders",
        "RFQ",
        "Payments",
        "Ledger",
        "System Health",
    ]


def test_superuser_navigation_includes_all_context_sections():
    security_service = SimpleNamespace(is_admin_identity=lambda _user: True)
    sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="platform_admin", base_role="platform_admin", active_context="platform_admin", email="admin@example.com", manufacturer_code=None),
            "security_service": security_service,
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )
    assert sections == [
        "My Profile",
        "Dashboard",
        "Notifications",
        "My Actions",
        "Manufacturers",
        "Products",
        "Product Approvals",
        "Marketplace",
        "Marketplace Orders",
        "Mandi Network",
        "Mandi Orders",
        "RFQ",
        "Jobs",
        "Platform Commission",
        "Payments",
        "Ledger",
        "System Health",
    ]


def test_security_service_builds_effective_superuser_context(tmp_path):
    security_service = SecurityService(
        encryption_service=EncryptionService(secret_seed="test-seed"),
        auth_service=SimpleNamespace(),
        admin_token_file=tmp_path / "admin_token.enc",
        manufacturer_token_dir=tmp_path / "manufacturer_tokens",
        runtime_tokens_dir=tmp_path / "runtime_tokens",
        require_verification_for_admin_runtime=False,
    )
    user = AuthUser(
        email="admin@example.com",
        name="Admin",
        role="platform_admin",
        base_role="platform_admin",
        active_context="manufacturer",
    )
    effective_user = security_service.build_effective_user(user)
    assert effective_user is not None
    assert effective_user.role == "manufacturer"
    assert effective_user.base_role == "platform_admin"
    assert effective_user.manufacturer_code == "ADMIN_MANU"


def test_master_data_contains_shared_categories_and_states():
    service = MasterDataService()
    categories = service.get_product_categories()
    states = service.get_indian_states_and_union_territories()
    assert "Grocery / Kirana" in categories
    assert "Other" in categories
    assert "Maharashtra" in states
    assert "Delhi" in states


def test_superadmin_summary_routes_use_dedicated_modules(monkeypatch):
    hits: list[str] = []
    app_context = {
        "current_user": SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: True),
    }
    monkeypatch.setattr("bootstrap.route_registry.render_rfq_summary_dashboard", lambda _ctx: hits.append("rfq"))
    monkeypatch.setattr("bootstrap.route_registry.render_commission_summary_dashboard", lambda _ctx: hits.append("commission"))

    render_route("RFQ", app_context)
    render_route("Platform Commission", app_context)

    assert hits == ["rfq", "commission"]


def test_superuser_supervisor_mode_routes_private_sections_to_safe_summaries(monkeypatch):
    hits: list[str] = []
    app_context = {
        "current_user": SimpleNamespace(role="platform_admin", base_role="platform_admin", active_context="platform_admin", email="admin@example.com", manufacturer_code=None),
        "session_user": SimpleNamespace(role="platform_admin", base_role="platform_admin", active_context="platform_admin", email="admin@example.com", manufacturer_code=None),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: True),
    }
    monkeypatch.setattr("bootstrap.route_registry.render_admin_dashboard", lambda _ctx, section="Dashboard": hits.append(section))
    render_route("Client Orders", app_context)
    render_route("Ledger", app_context)
    render_route("Mandi Orders", app_context)
    assert hits == ["Client Orders", "Ledger", "Mandi Orders"]


def test_role_navigation_map_is_normalized():
    assert "platform_admin" in ROLE_NAVIGATION_MAP
    flattened = [item for groups in ROLE_NAVIGATION_MAP.values() for _group, sections in groups for item in sections]
    assert "Mandiplace" not in flattened
    assert "Mandiplace Orders" not in flattened
    assert "Commission Summary" not in flattened
    assert "Public Orders" not in flattened
    assert "rfq" not in flattened


def test_manufacturer_navigation_has_clients_not_manufacturers():
    security_service = SimpleNamespace(is_admin_identity=lambda _user: False)
    sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101"),
            "security_service": security_service,
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )
    assert "Clients" in sections
    assert "Manufacturers" not in sections


def test_superuser_context_can_preview_client_dashboard_without_losing_admin_identity(monkeypatch):
    hits: list[str] = []
    app_context = {
        "current_user": SimpleNamespace(role="client", base_role="platform_admin", active_context="client", email="admin@example.com", manufacturer_code="ADMIN_MANU"),
        "session_user": SimpleNamespace(role="platform_admin", base_role="platform_admin", active_context="client", email="admin@example.com", manufacturer_code=None),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: True),
    }
    monkeypatch.setattr("bootstrap.route_registry.render_client_dashboard", lambda _ctx: hits.append("client"))
    render_route("Dashboard", app_context)
    assert hits == ["client"]


def test_unauthenticated_routes_render_global_login_page(monkeypatch):
    hits: list[str] = []
    app_context = {
        "current_user": None,
        "session_user": None,
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
    }
    monkeypatch.setattr("bootstrap.route_registry.render_login_page", lambda _ctx: hits.append("login"))
    render_route("Dashboard", app_context)
    render_route("Marketplace", app_context)
    assert hits == ["login", "login"]


def test_public_buyer_profile_edit_persists_complete_fields(tmp_path):
    governance, drive, _client_service = _build_persistence_stack(tmp_path)
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups_public",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history_public",
    )
    from services.public_buyer_service import PublicBuyerService
    buyer_service = PublicBuyerService(
        public_buyers_root=tmp_path / "public_buyers",
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=type("Allocator", (), {"allocate": lambda self, domain: "PB-2026-000001"})(),
    )
    buyer = buyer_service.register_or_get(email="buyer@example.com", full_name="Buyer")
    updated = buyer_service.upsert_profile(
        buyer["public_buyer_id"],
        {
            "full_name": "Buyer User",
            "mobile": "9876543210",
            "alternate_mobile": "9123456789",
            "business_name": "Buyer Home",
            "city": "Pune",
            "state": "Maharashtra",
            "pin_code": "411001",
            "delivery_address": "Flat 101",
            "landmark": "Near market",
            "preferred_payment_mode": "UPI",
            "delivery_instructions": "Ring bell",
        },
    )
    assert updated["profile_status"] == "COMPLETE"
    assert updated["preferred_payment_mode"] == "UPI"
    assert updated["address"]["line1"] == "Flat 101"
