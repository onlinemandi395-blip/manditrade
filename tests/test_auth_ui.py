from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.route_registry import can_access_route
from bootstrap.app_bootstrap import resolve_navigation_sections


def test_google_login_is_rendered_in_sidebar_session_area():
    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    assert "## Session" in bootstrap_content
    assert "mt-sidebar-google-login" in bootstrap_content
    assert "render_configurable_link_button(" in bootstrap_content
    assert "build_authorization_url(flow_type=app_context[\"oauth_callback_service\"].LOGIN)" in bootstrap_content
    assert "render_new_tab_link_button" not in access_content
    assert "mt-google-login-btn" not in bootstrap_content


def test_login_navigation_mode_supports_new_tab_and_same_tab():
    shell_content = Path("components/ui_shell.py").read_text(encoding="utf-8")
    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")
    config_content = Path("configs/system_config.json").read_text(encoding="utf-8")
    assert 'render_new_tab_link_button' in shell_content
    assert 'render_same_tab_link_button' in shell_content
    assert '"login_navigation_mode": "new_tab"' in config_content
    assert "_resolve_login_navigation_mode" in bootstrap_content


def test_marketplace_does_not_render_separate_public_buyer_login():
    content = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")
    assert "Continue with Google as Public Buyer" not in content
    assert "Prepare Google Sign-In As Public Buyer" not in content


def test_mock_login_and_manual_google_key_fields_are_not_visible_in_access_surfaces():
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    profile_content = Path("modules/profile/dashboard.py").read_text(encoding="utf-8")
    admin_content = Path("modules/admin/manufacturers.py").read_text(encoding="utf-8")
    onboarding_content = Path("modules/onboarding/manufacturer_onboarding.py").read_text(encoding="utf-8")

    assert "mock login" not in access_content.lower()
    combined = "\n".join([profile_content, admin_content, onboarding_content]).lower()
    assert 'text_input("client id"' not in combined
    assert "text_input('client id'" not in combined
    assert 'text_input("client secret"' not in combined
    assert "text_input('client secret'" not in combined
    assert 'text_input("api key"' not in combined
    assert "text_input('api key'" not in combined


def test_connected_accounts_ui_visibility_rules_are_role_scoped():
    profile_content = Path("modules/profile/dashboard.py").read_text(encoding="utf-8")
    assert "Connected Accounts" in profile_content
    assert "if current_user.role in {\"manufacturer\", \"admin_as_manufacturer\"}" in profile_content


def test_only_one_login_renderer_exists():
    route_content = Path("bootstrap/route_registry.py").read_text(encoding="utf-8")
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    assert "render_login_page" in route_content
    assert "def render_login_page" in access_content


def test_same_tab_google_link_never_uses_blank_target():
    shell_content = Path("components/ui_shell.py").read_text(encoding="utf-8")
    assert "target='_self'" in shell_content
    assert "target='_blank'" in shell_content
    same_tab_block = shell_content.split("def render_same_tab_link_button", 1)[1].split("def render_new_tab_link_button", 1)[0]
    assert "_blank" not in same_tab_block


def test_new_tab_google_link_uses_blank_target_and_noopener():
    shell_content = Path("components/ui_shell.py").read_text(encoding="utf-8")
    new_tab_block = shell_content.split("def render_new_tab_link_button", 1)[1].split("def render_configurable_link_button", 1)[0]
    assert "target='_blank'" in new_tab_block
    assert "rel='noopener noreferrer'" in new_tab_block


def test_route_guard_blocks_unauthorized_normal_users():
    app_context = {"security_service": SimpleNamespace(is_admin_identity=lambda _user: False), "session_user": None}
    manufacturer = SimpleNamespace(role="manufacturer")
    client = SimpleNamespace(role="client")
    public_buyer = SimpleNamespace(role="public_buyer")
    worker = SimpleNamespace(role="worker")
    assert can_access_route(manufacturer, "Inventory", app_context) is False
    assert can_access_route(manufacturer, "System Health", app_context) is False
    assert can_access_route(manufacturer, "Manufacturers", app_context) is False
    assert can_access_route(manufacturer, "Clients", app_context) is True
    assert can_access_route(client, "Inventory", app_context) is False
    assert can_access_route(client, "System Health", app_context) is True
    assert can_access_route(public_buyer, "Marketplace", app_context) is True
    assert can_access_route(public_buyer, "RFQ", app_context) is False
    assert can_access_route(public_buyer, "Ledger", app_context) is False
    assert can_access_route(worker, "Payments", app_context) is False
    assert can_access_route(worker, "Jobs", app_context) is True


def test_unauthenticated_navigation_shows_dashboard_only():
    sections = resolve_navigation_sections(
        {
            "current_user": None,
            "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )
    assert sections == ["Dashboard"]


def test_unauthenticated_navigation_hides_marketplace_and_access():
    sections = resolve_navigation_sections(
        {
            "current_user": None,
            "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )
    assert "Marketplace" not in sections
    assert "Access" not in sections


def test_prelogin_has_exactly_one_continue_with_google_render_path():
    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    combined = "\n".join([bootstrap_content, access_content])
    assert combined.count("Continue with Google") == 1


def test_main_page_does_not_render_continue_with_google():
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    assert "Continue with Google" not in access_content


def test_no_mock_or_demo_login_visible_in_access_surface():
    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8").lower()
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8").lower()
    combined = "\n".join([bootstrap_content, access_content])
    assert "mock login" not in combined
    assert "demo login" not in combined


def test_normal_ui_files_hide_debug_and_runtime_copy():
    files = [
        Path("bootstrap/app_bootstrap.py"),
        Path("modules/access/dashboard.py"),
        Path("modules/marketplace/dashboard.py"),
        Path("modules/notifications/dashboard.py"),
        Path("modules/payments/dashboard.py"),
        Path("modules/profile/dashboard.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)
    banned_phrases = [
        "oauth session initialized",
        "long-lived admin runtime",
        "local oauth session mode",
        "client_id suffix",
        "secrets override",
        "fallback active",
        "no_access_mapping",
        "use central login",
    ]
    for phrase in banned_phrases:
        assert phrase not in combined


def test_sidebar_navigation_groups_are_rendered_from_central_map():
    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")
    assert "services.navigation_service" in bootstrap_content
    assert 'st.caption(group.upper())' in bootstrap_content
