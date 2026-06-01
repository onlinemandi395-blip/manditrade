from __future__ import annotations

from pathlib import Path

from services.navigation_service import ROLE_NAVIGATION_MAP, flatten_navigation_groups


def test_all_central_navigation_items_are_registered_in_route_registry_source():
    route_content = Path("bootstrap/route_registry.py").read_text(encoding="utf-8")
    for role, groups in ROLE_NAVIGATION_MAP.items():
        if role in {"unauthenticated", "pending_user"}:
            continue
        for section in flatten_navigation_groups(groups):
            assert f'"{section}"' in route_content or f"'{section}'" in route_content


def test_operational_pages_use_tabs_and_metric_buttons():
    files = [
        Path("modules/actions/dashboard.py"),
        Path("modules/notifications/dashboard.py"),
        Path("modules/profile/dashboard.py"),
        Path("modules/manufacturer/dashboard.py"),
        Path("modules/client/dashboard.py"),
        Path("modules/mahajan/dashboard.py"),
        Path("modules/payments/dashboard.py"),
        Path("modules/ledger/dashboard.py"),
        Path("modules/public_orders/dashboard.py"),
        Path("modules/analytics/dashboard.py"),
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "st.tabs(" in content
        assert "render_metric_button_row" in content


def test_page_ui_helper_exists_for_clickable_metric_dashboards():
    content = Path("utils/page_ui.py").read_text(encoding="utf-8")
    assert "def render_metric_card_button" in content
    assert "def set_active_tab_from_metric" in content
    assert "def render_empty_state" in content


def test_mahajan_profile_has_dedicated_renderer():
    content = Path("modules/profile/dashboard.py").read_text(encoding="utf-8")
    assert "def _render_mahajan_profile" in content
    assert 'if current_user.role == "mahajan"' in content
