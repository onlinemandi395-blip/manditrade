from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.admin.dashboard import render_admin_dashboard
from modules.onboarding.manufacturer_onboarding import render_manufacturer_onboarding
from services.action_center_service import ActionCenterService
from services.domain_paths_service import DomainPathsService
from services.file_lock_service import FileLockService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.manufacturer_onboarding_service import ManufacturerOnboardingService
from services.notification_center_service import NotificationCenterService
from services.product_catalog_service import ProductCatalogService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.fake_storage import DriveStub, JsonServiceStub
from tests.helpers.failure_injector import GmailStub, LoggingStub


def _build_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    id_allocator = IdAllocatorService(tmp_path / "ids.json", FileLockService())
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
    onboarding = ManufacturerOnboardingService(drive, governance, safe_write, json_service, id_allocator_service=id_allocator)
    notification_center = NotificationCenterService(
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=id_allocator,
        domain_paths_service=DomainPathsService(drive_service=drive),
    )
    gmail_service = GmailStub()
    product_catalog = ProductCatalogService(
        governance_service=governance,
        id_allocator_service=id_allocator,
        notification_center_service=notification_center,
        gmail_service=gmail_service,
        admin_email="admin@example.com",
    )
    return governance, onboarding, product_catalog, notification_center, gmail_service


def test_manufacturer_onboarding_completes_with_active_status(tmp_path):
    governance, onboarding, _product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    created = onboarding.create_manufacturer(
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
    stored = governance.get_manufacturer("MANU101")
    assert created["status"] == "ACTIVE"
    assert stored["status"] == "ACTIVE"
    assert created["business_name"] == "Shree Agro Traders"
    assert created["manufacturer_id"].startswith("MANU-")


def test_manufacturer_onboarding_does_not_require_platform_approval_action(tmp_path):
    governance, onboarding, _product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    onboarding.create_manufacturer(
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
    _governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
        description="Premium rice bags",
        suggested_mandi_price=40,
        suggested_mrp=50,
        visibility_request="MANDI_NETWORK",
        minimum_order_qty=10,
        available_for_public_sale=False,
        available_for_mandi_network=True,
        image_url="https://example.com/rice.png",
    )
    assert product["status"] == "PROPOSED"
    assert product["created_by_manufacturer_id"] == "MANU101"
    assert product["suggested_mandi_price"] == 40.0


def test_platform_admin_can_approve_proposed_product(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
        suggested_mandi_price=40,
        suggested_mrp=50,
    )
    approved = product_catalog.approve_product(
        product_id=product["product_id"],
        approved_by="PLATFORM_ADMIN",
        approved_mandi_price=40,
        approved_mrp=50,
        category="Grain",
        unit="kg",
        approved_visibility="PUBLIC",
        admin_note="Approved for main catalog.",
    )
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert approved["status"] == "ACTIVE"
    assert stored["approved_by"] == "PLATFORM_ADMIN"
    assert stored["mandi_price"] == 40.0
    assert stored["approved_visibility"] == "PUBLIC"


def test_platform_admin_can_reject_proposed_product(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    rejected = product_catalog.reject_product(
        product_id=product["product_id"],
        approved_by="PLATFORM_ADMIN",
        admin_note="Duplicate commodity request.",
    )
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert rejected["status"] == "REJECTED"
    assert stored["admin_note"] == "Duplicate commodity request."


def test_platform_admin_can_update_approved_product(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
        suggested_mandi_price=40,
        suggested_mrp=50,
    )
    product_catalog.approve_product(
        product_id=product["product_id"],
        approved_by="PLATFORM_ADMIN",
        approved_mandi_price=40,
        approved_mrp=50,
        approved_visibility="PUBLIC",
    )
    updated = product_catalog.update_product(
        product_id=product["product_id"],
        updated_by="PLATFORM_ADMIN",
        updates={
            "name": "Steam Rice",
            "approved_mandi_price": 42,
            "approved_mrp": 55,
            "minimum_order_qty": 5,
            "visible": True,
            "admin_note": "Adjusted after review.",
        },
    )
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert updated["name"] == "Steam Rice"
    assert stored["mandi_price"] == 42.0
    assert stored["mrp"] == 55.0
    assert stored["minimum_order_qty"] == 5
    assert stored["admin_note"] == "Adjusted after review."


def test_platform_admin_can_delete_product(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    assert product_catalog.delete_product(product_id=product["product_id"]) is True
    archived = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert archived["status"] == "ARCHIVED"
    assert archived["visible"] is False


def test_public_buyers_only_see_active_public_products(tmp_path):
    _governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    proposed = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    active = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Wheat",
        category="Grain",
        unit="kg",
        available_for_public_sale=True,
    )
    product_catalog.approve_product(
        product_id=active["product_id"],
        approved_by="PLATFORM_ADMIN",
        approved_mandi_price=32,
        approved_mrp=39,
        category="Grain",
        unit="kg",
        approved_visibility="PUBLIC",
    )
    visible_to_public_buyer = product_catalog.list_products(include_pending=False, viewer_role="public_buyer")
    assert [item["product_id"] for item in visible_to_public_buyer] == [active["product_id"]]
    assert all(item["status"] == "ACTIVE" for item in visible_to_public_buyer)
    assert proposed["product_id"] not in [item["product_id"] for item in visible_to_public_buyer]
    assert "comments" not in visible_to_public_buyer[0]


def test_manufacturer_and_admin_can_see_proposed_products_in_expected_scopes(tmp_path):
    _governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    own_proposed = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    other_proposed = product_catalog.propose_product(
        created_by="MANU202",
        created_by_email="other@example.com",
        name="Oil",
        category="Oil",
        unit="L",
    )
    manufacturer_view = product_catalog.list_products(viewer_role="manufacturer", viewer_code="MANU101")
    admin_view = product_catalog.list_products(viewer_role="platform_admin", include_pending=True)
    assert own_proposed["product_id"] in [item["product_id"] for item in manufacturer_view]
    assert other_proposed["product_id"] not in [item["product_id"] for item in manufacturer_view]
    assert {own_proposed["product_id"], other_proposed["product_id"]}.issubset({item["product_id"] for item in admin_view})


def test_admin_can_comment_on_product_proposal_and_manufacturer_gets_notification(tmp_path):
    governance, _onboarding, product_catalog, notification_center, gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    admin_user = SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    comment = product_catalog.add_product_comment(product["product_id"], admin_user, "Please clarify unit: kg or bag?")
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    notifications = notification_center.list_notifications("MANU101")
    assert comment["author_role"] == "PLATFORM_ADMIN"
    assert stored["clarification_status"] == "ADMIN_QUERY"
    assert stored["comments"][0]["message"] == "Please clarify unit: kg or bag?"
    assert notifications[0]["type"] == "PRODUCT_PROPOSAL_COMMENTED"
    assert gmail_service.sent[0]["notification_type"] == "product_proposal_commented"


def test_manufacturer_can_reply_to_own_product_proposal_and_admin_gets_notification(tmp_path):
    governance, _onboarding, product_catalog, notification_center, gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    admin_user = SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    manufacturer_user = SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101")
    product_catalog.add_product_comment(product["product_id"], admin_user, "Please clarify unit: kg or bag?")
    reply = product_catalog.add_product_comment(product["product_id"], manufacturer_user, "It is sold in kg.")
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    notifications = notification_center.list_notifications("MANU101")
    assert reply["author_role"] == "MANUFACTURER"
    assert stored["clarification_status"] == "MANUFACTURER_REPLIED"
    assert notifications[-1]["type"] == "PRODUCT_PROPOSAL_REPLIED"
    assert notifications[-1]["user_id"] == "admin@example.com"
    assert gmail_service.sent[-1]["notification_type"] == "product_proposal_replied"


def test_unrelated_manufacturer_and_public_buyer_cannot_see_or_comment_product_proposal(tmp_path):
    _governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    unrelated_manufacturer = SimpleNamespace(role="manufacturer", email="other@example.com", manufacturer_code="MANU202")
    public_buyer_user = SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None)
    with pytest.raises(PermissionError):
        product_catalog.list_product_comments(product["product_id"], unrelated_manufacturer)
    with pytest.raises(PermissionError):
        product_catalog.add_product_comment(product["product_id"], unrelated_manufacturer, "I can see this?")
    with pytest.raises(PermissionError):
        product_catalog.list_product_comments(product["product_id"], public_buyer_user)


def test_comment_thread_read_tracking_and_clarification_resolution(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    admin_user = SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    manufacturer_user = SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101")
    product_catalog.add_product_comment(product["product_id"], admin_user, "Please clarify MOQ.")
    comments = product_catalog.list_product_comments(product["product_id"], manufacturer_user)
    assert "MANU101" in comments[0]["read_by"]
    resolved = product_catalog.mark_clarification_resolved(product["product_id"], admin_user)
    assert resolved["clarification_status"] == "RESOLVED"
    stored = next(item for item in governance.list_products() if item["product_id"] == product["product_id"])
    assert stored["comments"][0]["message"] == "Please clarify MOQ."


def test_approval_blocked_while_admin_query_unresolved(tmp_path):
    _governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    admin_user = SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    product_catalog.add_product_comment(product["product_id"], admin_user, "Need pricing justification.")
    with pytest.raises(ValueError, match="clarification is unresolved"):
        product_catalog.approve_product(
            product_id=product["product_id"],
            approved_by="PLATFORM_ADMIN",
            approved_mandi_price=40,
            approved_mrp=50,
            approved_visibility="PUBLIC",
        )


def test_product_comment_actions_are_added_for_manufacturer_and_admin(tmp_path):
    governance, _onboarding, product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
    product = product_catalog.propose_product(
        created_by="MANU101",
        created_by_email="owner@example.com",
        name="Rice",
        category="Grain",
        unit="kg",
    )
    admin_user = SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    manufacturer_user = SimpleNamespace(role="manufacturer", email="owner@example.com", manufacturer_code="MANU101")
    product_catalog.add_product_comment(product["product_id"], admin_user, "Clarify category mapping.")
    action_center = ActionCenterService(
        governance_service=governance,
        gmail_service=SimpleNamespace(read_queue=lambda: []),
        notification_center_service=None,
        ledger_service=SimpleNamespace(list_ledgers=lambda _manufacturer_code: []),
        order_query_service=SimpleNamespace(list_orders=lambda _manufacturer_code: [], list_orders_for_client=lambda _manufacturer_code, _email: []),
        procurement_query_service=SimpleNamespace(list_procurement_requests=lambda _manufacturer_code: []),
        dual_inventory_service=SimpleNamespace(list_inventory=lambda _manufacturer_code: {"items": []}),
    )
    manufacturer_actions = action_center.get_actions(manufacturer_user)
    assert any(item["type"] == "PRODUCT_PROPOSAL_NEEDS_REPLY" for item in manufacturer_actions)

    product_catalog.add_product_comment(product["product_id"], manufacturer_user, "Mapped to grain category.")
    admin_actions = action_center.get_actions(admin_user)
    assert any(item["type"] == "PRODUCT_PROPOSAL_REPLY_PENDING_REVIEW" for item in admin_actions)


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
        self.session_state = {}

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

    def text_area(self, *_args, value="", **_kwargs):
        return value

    def caption(self, *_args, **_kwargs):
        return None

    def dataframe(self, *_args, **_kwargs):
        return None

    def success(self, *_args, **_kwargs):
        return None

    def code(self, *_args, **_kwargs):
        return None

    def button(self, *_args, **_kwargs):
        return False

    def json(self, *_args, **_kwargs):
        return None

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
    governance, onboarding, _product_catalog, _notification_center, _gmail_service = _build_stack(tmp_path)
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
