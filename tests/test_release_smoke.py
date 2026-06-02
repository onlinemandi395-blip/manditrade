from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.app_bootstrap import resolve_navigation_sections
from bootstrap.route_registry import can_access_route, render_route


def _app_context_for_role(role: str | None) -> dict:
    user = None if role is None else SimpleNamespace(role=role, email=f"{role or 'anon'}@example.com", manufacturer_code="MANU101" if role == "manufacturer" else None)
    session_user = None if role != "platform_admin" else SimpleNamespace(role="platform_admin", email="admin@example.com", manufacturer_code=None)
    return {
        "current_user": user,
        "session_user": session_user,
        "security_service": SimpleNamespace(is_admin_identity=lambda candidate: bool(candidate and getattr(candidate, "role", "") == "platform_admin")),
        "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
    }


def test_all_role_navigation_routes_render_without_exception(monkeypatch):
    hits: list[str] = []

    def _capture(name: str):
        return lambda *_args, **_kwargs: hits.append(name)

    patch_targets = [
        "render_login_page",
        "render_pending_user_dashboard",
        "render_actions_dashboard",
        "render_account_status_dashboard",
        "render_analytics_dashboard",
        "render_commission_summary_dashboard",
        "render_commission_dashboard",
        "render_admin_dashboard",
        "render_operations_dashboard",
        "render_mahajans_dashboard",
        "render_inventory_summary_dashboard",
        "render_manufacturers_dashboard",
        "render_mahajan_dashboard",
        "render_product_approvals_dashboard",
        "render_rfq_summary_dashboard",
        "render_inventory_management",
        "render_jobs_dashboard",
        "render_ledger_dashboard",
        "render_manufacturer_dashboard",
        "render_marketplace_dashboard",
        "render_notifications_dashboard",
        "render_manufacturer_onboarding",
        "render_orders_dashboard",
        "render_dispatch_management",
        "render_payments_dashboard",
        "render_my_profile_dashboard",
        "render_procurement_dashboard",
        "render_products_dashboard",
        "render_public_orders_dashboard",
        "render_raw_materials_dashboard",
        "render_suta_mandi_dashboard",
        "render_health_dashboard",
    ]
    for target in patch_targets:
        monkeypatch.setattr(f"bootstrap.route_registry.{target}", _capture(target))

    for role in ["platform_admin", "manufacturer", "mahajan", "public_buyer", "worker"]:
        app_context = _app_context_for_role(role)
        sections = resolve_navigation_sections(app_context)
        assert sections, f"No navigation sections resolved for {role}"
        for section in sections:
            before = len(hits)
            render_route(section, app_context)
            assert len(hits) == before + 1, f"{role} route {section} did not dispatch a renderer"


def test_unauthorized_routes_do_not_leak(monkeypatch):
    hits: list[str] = []
    monkeypatch.setattr("bootstrap.route_registry.render_account_status_dashboard", lambda *_args, **_kwargs: hits.append("denied"))
    monkeypatch.setattr("bootstrap.route_registry.render_marketplace_dashboard", lambda *_args, **_kwargs: hits.append("marketplace"))
    monkeypatch.setattr("bootstrap.route_registry.render_health_dashboard", lambda *_args, **_kwargs: hits.append("health"))

    manufacturer_ctx = _app_context_for_role("manufacturer")
    worker_ctx = _app_context_for_role("worker")

    assert can_access_route(manufacturer_ctx["current_user"], "System Health", manufacturer_ctx) is False
    render_route("System Health", manufacturer_ctx)
    assert hits[-1] == "denied"

    assert can_access_route(worker_ctx["current_user"], "Marketplace", worker_ctx) is False
    render_route("Marketplace", worker_ctx)
    assert hits[-1] == "denied"


def test_prelogin_navigation_and_sidebar_login_surface():
    sections = resolve_navigation_sections(_app_context_for_role(None))
    assert sections == ["Dashboard"]

    bootstrap_content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")
    assert "## Session" in bootstrap_content
    assert "Continue with Google" in bootstrap_content


def test_no_duplicate_login_route_copy():
    combined = "\n".join(
        [
            Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8"),
            Path("modules/access/dashboard.py").read_text(encoding="utf-8"),
        ]
    )
    assert combined.count("Continue with Google") == 1
