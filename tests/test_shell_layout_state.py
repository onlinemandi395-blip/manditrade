from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.session_state_service import SessionStateService


def test_collapse_transient_sidebar_state_resets_overlay_flags(monkeypatch):
    fake_streamlit = SimpleNamespace(
        session_state={
            "sidebar_notifications_open": True,
            "sidebar_quick_actions_open": True,
            "sidebar_context_switch_open": True,
            "sidebar_mobile_overlay_open": True,
            "sidebar_expanded_groups": {"ops": True},
            "mt_state::overlay::notifications": "open",
        }
    )
    monkeypatch.setattr("services.session_state_service.st", fake_streamlit)

    service = SessionStateService()
    service.collapse_transient_sidebar_state()

    assert fake_streamlit.session_state["sidebar_notifications_open"] is False
    assert fake_streamlit.session_state["sidebar_quick_actions_open"] is False
    assert fake_streamlit.session_state["sidebar_context_switch_open"] is False
    assert fake_streamlit.session_state["sidebar_mobile_overlay_open"] is False
    assert fake_streamlit.session_state["sidebar_expanded_groups"] == {}
    assert "mt_state::overlay::notifications" not in fake_streamlit.session_state


def test_set_navigation_collapses_transient_state_on_route_change(monkeypatch):
    fake_streamlit = SimpleNamespace(
        session_state={
            "sidebar_section": "Dashboard",
            "sidebar_notifications_open": True,
        }
    )
    monkeypatch.setattr("services.session_state_service.st", fake_streamlit)

    service = SessionStateService()
    service.set_navigation("Payments")

    assert fake_streamlit.session_state["sidebar_notifications_open"] is False
    assert fake_streamlit.session_state["sidebar_section"] == "Payments"


def test_layout_css_uses_dynamic_viewport_and_visible_forms():
    tokens = Path("assets/styles/design_tokens.css").read_text(encoding="utf-8")
    theme = Path("assets/styles/manditrade_3d.css").read_text(encoding="utf-8")

    assert "min-height: 100vh;" in tokens
    assert "overflow: visible;" in tokens
    assert "position: sticky;" in tokens
    assert "div[data-testid=\"stForm\"]" in tokens
    assert "overflow: visible;" in theme


def test_bootstrap_navigation_and_logout_use_sidebar_collapse_helper():
    content = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")

    assert "collapse_transient_sidebar_state()" in content
    assert "st.rerun()" in content
