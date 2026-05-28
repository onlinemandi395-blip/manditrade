from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.admin.dashboard import render_admin_dashboard
from modules.onboarding.manufacturer_onboarding import render_manufacturer_onboarding
from services.action_center_service import ActionCenterService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.manufacturer_onboarding_service import ManufacturerOnboardingService
from services.product_catalog_service import ProductCatalogService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
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
    governance = GovernanceService(tmp_path / "governance", safe_drive_write_service=safe_write)
    governance.ensure_files()
    drive = DriveStub(tmp_path / "manufacturers", json_service)
    drive.safe_drive_write_service = safe_write
    onboarding = ManufacturerOnboardingService(drive, governance, safe_write, json_service)
    product_catalog = ProductCatalogService(
        governance_service=governance,
        id_allocator_service=IdAllocatorService(tmp_path / "ids.json", FileLockService()),
    )
    return governance, onboarding, product_catalog


def test_manufacturer_onboarding_completes_with_active_status(tmp_path):
    governance, onboarding, _product_catalog = _build_stack(tmp_path)
    created = onboarding.create_manufacturer(
        manufacturer_code="MANU101",
        manufacturer_name="Shree Agro Traders",
        owner_email="owner@example.com",
        city="Jaipur",
        created_by="admin@example.com",
    )
    stored = governance.get_manufacturer("MANU101")
    assert created["status"] == "ACTIVE"
    assert stored["status"] == "ACTIVE"


def test_manufacturer_onboarding_does_not_require_platform_approval_action(tmp_path):
    governance, onboarding, _product_catalog = _build_stack(tmp_path)
    onboarding.create_manufacturer(
        manufacturer_code="MANU101",
        manufacturer_name="Shree Agro Traders",
        owner_email="owner@example.com",
        city="Jaipur",
        created_by="admin@example.com",
    )
    assert all(item.get("status") == "ACTIVE" for item in governance.list_manufacturers())
    actions = ActionCenterService(
        governance_service=governance,
        gmail_service=SimpleNamespace(read_queue=lambda: []),
        notification_center_service=None,
        ledger_service=None,
        order_query_service=None,
        procurement_query_service=None,
        dual_inventory_service=None,
    ).get_actions(SimpleNamespace(role="platform_admin"))
    assert all(item["type"] != "APPROVE_MANUFACTURER" for item in actions)


def test_manufacturer_can_propose_product_with_proposed_status(tmp_path):
    _governance, _onboarding, product_catalog = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    assert product["status"] == "PROPOSED"
    assert product["created_by"] == "MANU101"


def test_platform_admin_can_approve_proposed_product(tmp_path):
    governance, _onboarding, product_catalog = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    approved = product_catalog.approve_product(
        product_id=product["product_id"],
        approved_by="PLATFORM_ADMIN",
        mandi_price=40,
        mrp=50,
        category="Grain",
        unit="kg",
        visible=True,
    )
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert approved["status"] == "ACTIVE"
    assert stored["approved_by"] == "PLATFORM_ADMIN"
    assert stored["mandi_price"] == 40.0


def test_clients_only_see_active_products(tmp_path):
    _governance, _onboarding, product_catalog = _build_stack(tmp_path)
    proposed = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    active = product_catalog.propose_product(
        created_by="MANU101",
        name="Wheat",
        category="Grain",
        unit="kg",
    )
    product_catalog.approve_product(
        product_id=active["product_id"],
        approved_by="PLATFORM_ADMIN",
        mandi_price=32,
        mrp=39,
        category="Grain",
        unit="kg",
        visible=True,
    )
    visible_to_client = product_catalog.list_products(include_pending=False, viewer_role="client")
    assert [item["product_id"] for item in visible_to_client] == [active["product_id"]]
    assert all(item["status"] == "ACTIVE" for item in visible_to_client)
    assert proposed["product_id"] not in [item["product_id"] for item in visible_to_client]


def test_manufacturer_and_admin_can_see_proposed_products_in_expected_scopes(tmp_path):
    _governance, _onboarding, product_catalog = _build_stack(tmp_path)
    own_proposed = product_catalog.propose_product(
        created_by="MANU101",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    other_proposed = product_catalog.propose_product(
        created_by="MANU202",
        name="Oil",
        category="Oil",
        unit="L",
    )
    manufacturer_view = product_catalog.list_products(viewer_role="manufacturer", viewer_code="MANU101")
    admin_view = product_catalog.list_products(viewer_role="platform_admin", include_pending=True)
    assert own_proposed["product_id"] in [item["product_id"] for item in manufacturer_view]
    assert other_proposed["product_id"] not in [item["product_id"] for item in manufacturer_view]
    assert {own_proposed["product_id"], other_proposed["product_id"]}.issubset({item["product_id"] for item in admin_view})


class _FakeColumn:
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, name):
        return getattr(self.parent, name)


class _FakeForm:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlitDashboard:
    def dataframe(self, *_args, **_kwargs):
        return None

    def info(self, *_args, **_kwargs):
        return None

    def success(self, *_args, **_kwargs):
        return None

    def rerun(self):
        return None

    def form(self, *_args, **_kwargs):
        raise AssertionError("Dashboard should not render onboarding forms.")


class _FakeStreamlitOnboarding:
    def __init__(self):
        self.form_calls = 0

    def columns(self, count):
        return [_FakeColumn(self) for _ in range(count)]

    def text_input(self, *_args, value="", **_kwargs):
        return value

    def selectbox(self, _label, options, index=0, **_kwargs):
        return options[index]

    def form_submit_button(self, *_args, **_kwargs):
        return False

    def markdown(self, *_args, **_kwargs):
        return None

    def dataframe(self, *_args, **_kwargs):
        return None

    def success(self, *_args, **_kwargs):
        return None

    def code(self, *_args, **_kwargs):
        return None

    def button(self, *_args, **_kwargs):
        return False

    def info(self, *_args, **_kwargs):
        return None

    def rerun(self):
        return None

    def form(self, *_args, **_kwargs):
        self.form_calls += 1
        return _FakeForm()


def test_dashboard_does_not_render_manufacturer_onboarding_form(monkeypatch):
    fake_st = _FakeStreamlitDashboard()
    monkeypatch.setattr("modules.admin.dashboard.st", fake_st)
    monkeypatch.setattr("modules.admin.dashboard.render_page_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.admin.dashboard.render_metric_grid", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.admin.dashboard.render_showcase_strip", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.admin.dashboard.render_dual_panel", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.admin.dashboard.render_section_intro", lambda *_args, **_kwargs: None)
    render_admin_dashboard(
        {
            "governance_service": SimpleNamespace(list_products=lambda: [], list_manufacturers=lambda: []),
            "action_center_service": SimpleNamespace(get_actions=lambda _user: []),
        }
    )


def test_onboarding_route_still_renders_manufacturer_onboarding_form(monkeypatch, tmp_path):
    fake_st = _FakeStreamlitOnboarding()
    governance, onboarding, _product_catalog = _build_stack(tmp_path)
    monkeypatch.setattr("modules.onboarding.manufacturer_onboarding.st", fake_st)
    monkeypatch.setattr("modules.onboarding.manufacturer_onboarding.render_page_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.onboarding.manufacturer_onboarding.render_metric_grid", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.onboarding.manufacturer_onboarding.render_section_intro", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("modules.onboarding.manufacturer_onboarding.render_metric_card", lambda *_args, **_kwargs: "")
    render_manufacturer_onboarding(
        {
            "current_user": SimpleNamespace(role="platform_admin", email="admin@example.com"),
            "manufacturer_onboarding_service": onboarding,
            "governance_service": governance,
        }
    )
    assert fake_st.form_calls >= 1
